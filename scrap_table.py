import requests
from bs4 import BeautifulSoup
import boto3
import uuid

def lambda_handler(event, context):
    # URL de la página web que contiene la tabla
    url = "https://ultimosismo.igp.gob.pe/api/ultimo-sismo/ajaxb/2026"

    # Me lo recomendo porque me bloqueaban
    headers_req = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
    }

    # Mejor hago un try except
    try:
        response = requests.get(url, headers=headers_req)
        response.raise_for_status()
        sismos_json = response.json()
    except Exception as e:
        return {
            'statusCode': 500,
            'body': f'Sigue sin funcionar con su API interna: {str(e)}'
        }

    ultimos_10_crudos = sismos_json[-10:][::-1]

    rows = []
    for sismo in ultimos_10_crudos:
        # Las llaves que vi en Vista Previa las copio aqui
        rows.append({
            'id': str(uuid.uuid4()),
            'Cod reporte': sismo.get('codigo', ''),
            'Referencia': sismo.get('referencia', ''),
            'Magnitud': str(sismo.get('magnitud', '')),
            'Fecha y hora': sismo.get('fecha_local', '')
        })

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
