import xml.etree.ElementTree as ET
import json

def xml_to_json(xml_file):
    tree = ET.parse(xml_file)
    root = tree.getroot()
    namespace = {'ss': 'urn:schemas-microsoft-com:office:spreadsheet'}

    data = {}
    rows = root.find('.//ss:Table', namespace).findall('ss:Row', namespace)

    # Extract headers
    headers = [cell.find('ss:Data', namespace).text for cell in rows[0].findall('ss:Cell', namespace)]

    # Extract data rows
    for row in rows[1:]:
        cells = row.findall('ss:Cell', namespace)
        row_data = {headers[i]: (cells[i].find('ss:Data', namespace).text if i < len(cells) else '') for i in range(len(headers))}
        symbol = row_data['Symbol']
        data[symbol] = row_data

    return data

xml_file = 'ReportOptimizer-83005574.xml'
json_data = xml_to_json(xml_file)

# Save JSON data to a file
with open('optimization_data.json', 'w') as json_file:
    json.dump(json_data, json_file, indent=4)
