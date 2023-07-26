from flask import Flask, request, jsonify
import json
import time
import os
from requests import get, post
from werkzeug.utils import secure_filename
import base64
import io

app = Flask(__name__)

ResultadosSucios = ""


def runAnalysis(data_bytes):
    global ResultadosSucios
    endpoint = r"https://reconocedor-csf.cognitiveservices.azure.com/"
    apim_key = "3f6c15d94d644bee943dfc87ace17e70"
    model_id = "26b436d2-cd14-4939-99ed-24244c0f9784"
    API_version = "v2.1"

    post_url = endpoint + "/formrecognizer/%s/custom/models/%s/analyze" % (API_version, model_id)
    params = {
        "includeTextDetails": True
    }

    headers = {
        'Content-Type': 'application/pdf',
        'Ocp-Apim-Subscription-Key': apim_key,
    }
    body = {
        "pages": ["1"]
    }

    try:
        print('Iniciando el análisis...')
        resp = post(url=post_url, data=data_bytes, headers=headers, params=params, json=body)
        if resp.status_code != 202:
            print("La solicitud POST para analizar ha fallado:\n%s" % json.dumps(resp.json()))
            return
        print("La solicitud POST para analizar ha tenido éxito:\n%s" % resp.headers)
        print()
        get_url = resp.headers["operation-location"]
    except Exception as e:
        print("La solicitud POST para analizar ha fallado:\n%s" % str(e))
        return

    n_tries = 15
    n_try = 0
    wait_sec = 5
    max_wait_sec = 60
    print('Obteniendo los resultados del análisis...')
    while n_try < n_tries:
        try:
            resp = get(url=get_url, headers={"Ocp-Apim-Subscription-Key": apim_key})
            resp_json = resp.json()
            if resp.status_code != 200:
                print("La solicitud GET para obtener los resultados del análisis ha fallado:\n%s" % json.dumps(resp_json))
                return
            status = resp_json["status"]
            if status == "succeeded":
                print("El análisis ha sido exitoso.")
                ResultadosSucios = json.dumps(resp_json["analyzeResult"]["documentResults"])
                print("Datos extraídos correctamente")
                return
            if status == "failed":
                print("El análisis ha fallado:\n%s" % json.dumps(resp_json))
                return
            time.sleep(wait_sec)
            n_try += 1
            wait_sec = min(2*wait_sec, max_wait_sec)
        except Exception as e:
            msg = "La solicitud GET para obtener los resultados del análisis ha fallado:\n%s" % str(e)
            print(msg)
            return
    print("La operación de análisis no se completó dentro del tiempo asignado.")


def extractor():
    global ResultadosSucios
    print("Extrayendo datos......")
    # Convertir los resultados sucios a un diccionario
    resultados_diccionario = json.loads(ResultadosSucios)
    campos_requeridos = [
        "NombreMunicipio",
        "FechaUltimoCambio",
        "NombreColonia",
        "TelFijo",
        "fechaInicioOperaciones",
        "NumeroExterior",
        "razonSocial",
        "nombreComercial",
        "Correo",
        "rfc",
        "NombreVialidad",
        "NumeroInterior",
        "NombreLocalidad",
        "CodigoPostal",
        "NombreEntidad",
        "EstatusPadron",
        "TipoVialidad",
        "EntreCalle",
        "Numero",
        "YCalle",
        "RegimenCapital",
        "LugarExpedicion",
        "FechaExpedicion"
    ]
    resultados_limpios = {}

    for campo in campos_requeridos:
        valor = "N/A"
        for item in resultados_diccionario:
            # Verificar si el campo está presente en el elemento actual
            if campo in item["fields"]:
                # Obtener el valor del campo del elemento actual
                valor = item["fields"][campo].get("valueString", "N/A")
                
                # Eliminar el texto "Postal:" del valor si el campo es "CodigoPostal"
                if campo == "CodigoPostal" and valor.startswith("Postal:"):
                    valor = valor[len("Postal:"):]
                
                break

            


        # Agregar el campo y su valor al diccionario de resultados limpios
        resultados_limpios[campo] = valor

    return resultados_limpios


@app.route('/extractor', methods=['POST'])
def extractor_api():
    # Obtener el código en base64 desde el cuerpo de la solicitud
    request_data = request.get_json()
    base64_code = request_data.get('base64_code')

    if not base64_code:
        return jsonify({'error': 'El código en base64 no se ha proporcionado.'}), 400

    try:
        # Decodificar el código en base64 a bytes
        pdf_bytes = base64.b64decode(base64_code)
    except Exception as e:
        return jsonify({'error': 'Error al decodificar el código en base64: {}'.format(str(e))}), 400

    # Ejecutar el análisis con los datos en formato PDF
    runAnalysis(pdf_bytes)
    resultados_limpios = extractor()
    # Devolver los resultados limpios como respuesta JSON
    return jsonify(resultados_limpios)


@app.route('/on', methods=['GET'])
def on():
    return "Servidor encendido en azure TXDX 1.0"

@app.route('/validar_pdf', methods=['POST'])
def validar_pdf():
    # Verificar si se envió un archivo en la solicitud
    if 'file' not in request.files:
        return jsonify({'error': 'No se ha enviado ningún archivo.'}), 400

    file = request.files['file']
    # Verificar si el nombre del archivo tiene una extensión de PDF
    if not file.filename.endswith('.pdf'):
        return jsonify({'error': 'El archivo no es un PDF válido.'}), 400

    # Si se llega a este punto, el archivo es un PDF válido
    return jsonify({'mensaje': 'El archivo es un PDF válido.'}), 200



if __name__ == '__main__':
    # Obtener el puerto asignado desde la variable de entorno
    port = int(os.environ.get("PORT", 5000))
    
    # Ejecutar la aplicación Flask en el puerto asignado
    app.run(host='0.0.0.0', port=port)
