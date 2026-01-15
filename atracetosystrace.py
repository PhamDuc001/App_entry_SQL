
import logging
import os
import sys
import zlib
import re
import io
def convert_trace(input_file):
    result = None

    with open(input_file, 'rb') as f:
        result = f.read()

    if not len(result) or not (b'\nTRACE:' in result):
        logging.warning(
            '\nNo atrace data was captured. Output file was not written.')
        raise Exception("invalid input file")

    parts = result.split(b'\nTRACE:', 1)

    data = parts[1]
    size = 4096
    trace_data = []
    for chunk in (data[i:i + size] for i in range(0, len(data), size)):
        trace_data.append(chunk.decode('latin-1'))
        

    trace_data = ''.join(trace_data)

    if trace_data:
        trace_data = strip_and_decompress_trace(trace_data)

    trace_data = fix_circular_traces(trace_data)
    # print(type(trace_data))
    if not trace_data:
        logging.warning(
            '\nNo atrace data was captured. Output file was not written.')
        raise Exception("invalid input file")
    else:
        # sys.stdout.write("\nConverting to systrace...")
        sys.stdout.flush()

    script_dir = os.path.dirname(os.path.abspath(__file__))
    html_prefix = read_asset(script_dir, 'prefix.html')
    html_suffix = read_asset(script_dir, 'suffix.html')
    trace_viewer_html = read_asset(script_dir, 'systrace_trace_viewer.html')
	

    html_bytesio = io.BytesIO()
    html_prefix = html_prefix.replace('{{SYSTRACE_TRACE_VIEWER_HTML}}', trace_viewer_html)
    html_bytesio.write(html_prefix.encode('latin-1'))

    html_bytesio.write(b'<!-- BEGIN TRACE -->\n')
    html_bytesio.write(b'  <script class="')
    html_bytesio.write(b'trace-data')
    html_bytesio.write(b'" type="application/text">\n')
    html_bytesio.write(trace_data.encode('utf-8'))
    html_bytesio.write(b'  </script>\n')
    html_bytesio.write(b'<!-- END TRACE -->\n')

    html_bytesio.write(html_suffix.encode('utf-8'))
    html_bytesio.seek(0)
    # print(" done")

    return html_bytesio


def read_asset(src_dir, filename):
    return open(os.path.join(src_dir, filename), encoding = "latin-1").read()

def strip_and_decompress_trace(trace_data):

    if trace_data.startswith('\r\n'):
        trace_data = trace_data.replace('\r\n', '\n')
    elif trace_data.startswith('\r\r\n'):
        trace_data = trace_data.replace('\r\r\n', '\n')

    trace_data = trace_data[1:]

    if not trace_data.startswith('# tracer'):
        trace_data = zlib.decompress(trace_data.encode('latin-1'))

    trace_data = trace_data.decode('latin-1').replace('\r', '')
    if 'tracing_mark_write.llvm' in trace_data:
        trace_data = re.sub(r'tracing_mark_write\.llvm\.\d+:', 'tracing_mark_write:', trace_data)
    
    while trace_data and trace_data[0] == '\n':
        trace_data = trace_data[1:]
    return trace_data

def fix_circular_traces(out):
    buffer_start_re = re.compile(r'^#+ CPU \d+ buffer started', re.MULTILINE)
    start_of_full_trace = 0

    while True:
        result = buffer_start_re.search(out, start_of_full_trace + 1)
        if result:
            start_of_full_trace = result.start()
        else:
            break

    if start_of_full_trace > 0:
        end_of_header = re.search(r'^[^#]', out, re.MULTILINE).start()
        out = out[:end_of_header] + out[start_of_full_trace:]
    return out
