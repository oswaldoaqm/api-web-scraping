import requests
from bs4 import BeautifulSoup
import boto3
import uuid

def lambda_handler(event, context):
    # URL de la página web que contiene la tabla
    url = "https://ultimosismo.igp.gob.pe/productos/reportes-sismicos"

    # Me lo recomendo porque me bloqueaban
    headers_req = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
    }

    # Realizar la solicitud HTTP a la página web
    response = requests.get(url, headers=headers_req)
    if response.status_code != 200:
        return {
            'statusCode': response.status_code,
            'body': 'Error al acceder a la página web del IGP'
        }

    # Parsear el contenido HTML de la página web
    soup = BeautifulSoup(response.content, 'html.parser')

    # Encontrar la tabla en el HTML
    table = soup.find('table')
    if not table:
        return {
            'statusCode': 404,
            'body': 'No se encontró la tabla en la página web'
        }

    # Extraer los encabezados de la tabla
    thead = table.find('thead')
    if thead:
        headers = [header.text.strip() for header in thead.find_all('th')]
    else:
        # Encabezados por porque algunos no agarra el thead
        headers = ['#', 'Cod reporte', 'Referencia', 'Magnitud', 'Fecha y hora', 'Accion']

    # Agarro los 10 ultimos sismos
    rows = []
    tbody = table.find('tbody')
    
    # El parser no encuentra el tbody así que itero por tr
    filas_html = tbody.find_all('tr') if tbody else table.find_all('tr')[1:]
    
    # Tomamos solo las primeras 10
    for row in filas_html[:10]:
        cells = row.find_all('td')
        if cells:
            row_data = {}
            row_data['id'] = str(uuid.uuid4())
            
            for i, cell in enumerate(cells):
                key = headers[i] if i < len(headers) else f'Columna_{i}'
                row_data[key] = cell.text.strip()
            
            rows.append(row_data)

    if len(rows) == 0:
        return {
            'statusCode': 404,
            'body': 'Se encontró la tabla, pero estaba vacía (sin etiquetas <td>).'
        }

    # Guardo los datos en DynamoDB
    dynamodb = boto3.resource('dynamodb')
    dynamo_table = dynamodb.Table('TablaWebScrapping')

    scan = dynamo_table.scan()
    with dynamo_table.batch_writer() as batch:
        for each in scan['Items']:
            batch.delete_item(
                Key={
                    'id': each['id']
                }
            )

    for r in rows:
        dynamo_table.put_item(Item=r)

    # Retornar el resultado como JSON
    return {
        'statusCode': 200,
        'body': rows
    }
