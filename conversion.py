import argparse
import pylightxl as xl
import pytz
import sys

from datetime import datetime

DEBUG = False
INPUT_SEPARATOR = ";"
OUTPUT_SEPARATOR = ","
MAX_LINES = 2**32
TIME_FORMAT = "%d.%m.%Y %H:%M"
SOURCE_TIMEZONE = "Europe/Helsinki"

STATIC_COLUMNS = [
    ("site", "2463453700"),
]

DATA_COLUMN_NAMES = dict(
    house_energy="kwh",
    outside_temperature="temperature",
)


def parse_float(raw_field):
    # Float parsing, input data uses "," as decimal separator
    if not raw_field:
        return None
    float_field = raw_field.replace(",", ".") if "," in raw_field else raw_field
    try:
        float_field = float(float_field)
    except ValueError:
        print("Could not parse '{}' as float".format(raw_field))
        if args.verbose:
            print("Full line: {}".format(line.strip()))
        raise

    return float_field


class BaseFile:
    def __init__(self, options):
        self.options = options
        self.file_name = options.file_name

        self.headers = ["time", DATA_COLUMN_NAMES[self.options.measurement], "name", "month", "year"]
        # Add header columns for static fields
        for column_name, _ in STATIC_COLUMNS:
            self.headers.append(column_name)

    def open():
        raise NotImplementedError()

    def close():
        raise NotImplementedError()

    def get_csv_lines():
        raise NotImplementedError()

    def get_header_line(self):
        return OUTPUT_SEPARATOR.join(self.headers)

    def __enter__(self):
        self.open()
        return self

    def __exit__(self, *args):
        self.close()

    @staticmethod
    def _parse_date_field(date_str):
        """Parse date in format "01.01.2017 01:00 - 02:00" into datetime"""
        try:
            full_time = datetime.strptime(date_str, TIME_FORMAT)
        except ValueError:
            print("Could not parse '{} {}' as datetime".format(date_field, time_field))
            return None
        # Ensure correct timezone regardless of system locale
        full_time.replace(tzinfo=pytz.timezone(SOURCE_TIMEZONE))
        return full_time


class CSVFile(BaseFile):
    fp = None

    def open(self):
        self.fp = open(self.file_name, "r")

    def close(self):
        if self.fp:
            self.fp.close()
            self.fp = None

    def get_csv_lines(self):
        if not self.fp:
            raise Exception("No file open")

        # Skip header row
        _ = self.fp.readline()
        field_count = 3  # TODO, currently "time,kwh,temperature", support free-form csv file later

        yield self.get_header_line()

        lines_read = 0
        previous_entry = None  # Detect duplicate time entries caused by DST change
        while not self.options.limit or lines_read < self.options.limit:
            line = self.fp.readline()
            if not line:  # Empty string returned on EOF, '\n' on blank lines
                break
            fields = line.strip().split(INPUT_SEPARATOR)
            lines_read += 1
            if len(fields) != field_count:
                print("Invalid number of fields ({} vs {}) on line {}".format(len(fields), field_count, lines_read))
                continue
            date_field, time_field, *data_fields = fields
            assert len(data_fields) == 1  # TODO support flexible csv format

            final_fields = []

            for raw_field in data_fields:
                field = parse_float(raw_field)
            if field is None:
                print("Skipping row {} as values missing".format(lines_read))
                continue
            final_fields.append(str(field))

            # Add time column
            date_str = "{} {}".format(date_field, time_field)
            full_time = self._parse_date_field(date_str)
            if not full_time:
                continue
            final_fields.insert(0, str(int(full_time.timestamp()))) 

            final_fields.append(self.options.measurement)

            final_fields.append(str(full_time.month))
            final_fields.append(str(full_time.year))

            # Add static columns
            for _, column_field in STATIC_COLUMNS:
                final_fields.append(column_field)

            if len(self.headers) != len(final_fields):
                raise ValueError("Row {} has invalid number of fields: {}".format(lines_read, line))

            if previous_entry and previous_entry[0] == final_fields[0]:
                # Times match, this is a autumn DST change.
                # In influxdb the last entry with identical timestamp overwrites
                # the previously written one, so sum kwh values of entries with identical timestamps
                for i in range(0, len(final_fields)):
                    if self.headers[i] == "house_energy":
                        final_fields[i] = str(float(previous_entry[i]) + float(final_fields[i]))
                        print("Detected duplicate entry on {}, summed kwh to {}".format(full_time, final_fields[1]))
            previous_entry = final_fields
            yield OUTPUT_SEPARATOR.join(final_fields)

        print("Read {} lines".format(lines_read))


class XLSXFile(BaseFile):
    db = None

    COLUMN_MAP = dict(
        house_energy=0,
        outside_temperature=1,
    )

    def open(self):
        self.db = xl.readxl(self.file_name)
        self.ws = self.db.ws(ws='Sähkönkulutus')

    def close(self):
        self.db = None


    def get_csv_lines(self):
        if not self.db:
            raise Exception("No file open")

        data_column_index = self.COLUMN_MAP.get(self.options.measurement)

        yield self.get_header_line()

        lines_read = 0
        # Data starts on third row
        for raw_time, *data_fields in self.ws.range(address="A3:C10000"):
            if not raw_time:
                break
            if self.options.limit and lines_read > self.options.limit:
                break
            lines_read += 1

            raw_field = data_fields[data_column_index]
            if not isinstance(raw_field, (int, float)):
                print("Skipping row {} as values missing".format(lines_read))
                continue
            final_fields = [str(float(raw_field))]

            # Add time column
            date_str = raw_time.split(' - ')[0]
            full_time = self._parse_date_field(date_str)
            if not full_time:
                continue
            final_fields.insert(0, str(int(full_time.timestamp()))) 

            final_fields.append(self.options.measurement)

            final_fields.append(str(full_time.month))
            final_fields.append(str(full_time.year))

            # Add static columns
            for _, column_field in STATIC_COLUMNS:
                final_fields.append(column_field)
            yield OUTPUT_SEPARATOR.join(final_fields)
            
        print("Read {} lines".format(lines_read))


    

def usage():
    print("Usage: {} input.csv".format(sys.argv[0]))

def parse_args():
    parser = argparse.ArgumentParser(description='Convert energy consumption CSV file to influxdb compatible format.')
    parser.add_argument('file_name',
                        help='Input file')
    parser.add_argument('measurement',
                        help='Name of the measurement')
    parser.add_argument('-o', '--output_file',
                        help='Output file to write CSV data in')
    parser.add_argument('-l', '--limit', type=int, default=0,
                        help='How many rows to process (defaults to all)')
    parser.add_argument('-t', '--type', choices=['csv', 'xlsx'], default='csv',
                        help='Type of input file')
    parser.add_argument('-v', '--verbose', action='store_true')
    return parser.parse_args()

HANDLER_MAP = dict(
        csv=CSVFile,
        xlsx=XLSXFile,
)

if __name__ == '__main__':
    args = parse_args()
    output_fp = None

    lines_written = 0
    print("Processing file {}".format(args.file_name))
    input_file_class = HANDLER_MAP.get(args.type, CSVFile)
    with input_file_class(args) as input_file:
        if args.output_file:
            output_fp = open(args.output_file, "w")

        for line in input_file.get_csv_lines():
            if args.verbose:
                print(line)
            if output_fp:
                output_fp.write(line)
                output_fp.write('\n')
                lines_written += 1

    if output_fp:
        output_fp.close()
        print("Wrote {} lines".format(lines_written))
