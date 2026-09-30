Implement endpoints for Flows
Updated: Jun 28, 2026
This guide explains how to implement an Endpoint to power WhatsApp Flows.
Flows with an endpoint must meet both reliability and performance requirements. For additional information, refer to the Flows Health and Monitoring guide.
Endpoint examples
Basic endpoint example
A Node.js endpoint example is available that you can clone to create your own endpoint and quickly prototype your flow. Follow the instructions in the README.md file to get started. You can clone the example code from GitHub⁠ and run it in any environment you prefer.
“Book an Appointment” endpoint example
Endpoint code is also available that can be used along with the “Book an Appointment” flow JSON template to complete the flow from start to finish. Follow the instructions in the README.md file to get started. You can clone the example code from GitHub⁠ and run it in any environment you prefer.
Set up an endpoint
Endpoints provide dynamic data for the screens and control routing. That is, upon screen submission, the flow can make a request to the endpoint to get the name of the next screen and the data to display on it. Also, the endpoint can instruct the flow to terminate and control whether an outgoing message should be sent to a chat as a result of the flow completion. The endpoint can additionally provide a data payload to be passed with a completion message.
Setting up an endpoint consists of the following steps:
Create a key pair and upload and sign the public key.
Set up the HTTP endpoint.
Implement Payload Encryption/Decryption.
Link the endpoint to your flow:
specify data_api_version in the Flow JSON and configure endpoint url, see reference for more details.
if the Flow was created through WhatsApp Manager, connect Meta App to it in “Edit Flow” page, see Flow Builder UI for more details.
After setting up an endpoint, implement its logic to handle requests:
Data Exchange
Error Notification
Health Check
Upload public key
Data exchanged with an endpoint is encrypted using a combination of symmetric and asymmetric encryption. You should have a key pair to enable encryption and upload the public key. Meta automatically signs the public key during upload.
Since Solution Partners manage multiple businesses, use a dedicated endpoint and an encryption key pair for each WABA.
Sign and upload the business public key
Cloud API
You will need to re-upload the public key in the following cases:
When you re-register your number.
When you start receiving webhooks with alerts about client side errors public-key-missing or public-key-signature-verification.
Set up HTTP endpoint
When the flow needs to exchange data with your endpoint, it makes an HTTP request to that endpoint. You should set up a server and provide its URL while configuring the flow, for example:
https://business.com/scheduleappointment
Your server must be enabled to receive and process POST requests, use HTTPS and have a valid TLS/SSL certificate installed. This certificate does not have to be used in payload encryption/decryption.
Implement encryption/decryption
The body of each request contains the encrypted payload and has the following form:
Sample Endpoint Request
{
    "encrypted_flow_data": "<ENCRYPTED_FLOW_DATA>",
    "encrypted_aes_key": "<ENCRYPTED_AES_KEY>",
    "initial_vector": "<INITIAL_VECTOR>"
}
Parameter	Description
encrypted_flow_data
string
Required. The encrypted request payload.
encrypted_aes_key
string
Required. The encrypted 128-bit AES key.
initial_vector
string
Required. The 128-bit initialization vector.
After processing the decrypted request, create a response and encrypt it before sending it back to the WhatsApp client. Encrypt the payload using the AES key received in the request and send it back as a Base64 string.
You can reference the following examples of how to decrypt and encrypt.
If a request cannot be decrypted, the endpoint should return HTTP 421 response status code (see Business Endpoint Error Codes for more details).
Sample Endpoint Response
curl -i -H "Content-Type: application/json" -X POST -d '{
"encrypted_flow_data":"4Wor0bpfvrNqnkH+XQZLn3HnU2Zi7hG\\/UHjISS93Fzn9J7youssaLeXlNUH",
"encrypted_aes_key":"<ufA0fXD1WzMS4f2aCyr2JI4KtV2X+puen78fLjjt7mI+NqITDCypLOlc2MLc0899ApX5FZI78Yp5ZObEvR\\/3SiOo04aOLAcZ5SGlqcQLL1npaHoTZCBkExjDr0+5F7w+a18hLCByc00nuDoVZvX7qKAYTwDJw==.>",
"initial_vector":"<G\\/1rq1naEOMR4TJHFvIs\\/Q==.>"
}' 'https://business.com/testing_flow'

HTTP/2 200
content-type: text/plain
content-length: 232
date: Wed, 06 Jul 2022 14:03:03 GMT

yZcJQaH3AqfzKgjn64vAcASaJrOMN27S6CESyU68WN/cDCP6abskoMa/pPjszXGKyyh/23lw84HW6ZilMfU6KL3j5AWwOx6GWNwtq8Aj7gz/Y7R+LccmJWxKo2UccMu5xJlduIFlFlOS1gAnOwKrk8wpuprsi4jAOspw3xO2uh3J883aC/csu/MhRPiYCaGGy/tTNvVDmb2Gw1WXFmpvLsZ/SBrgG0cDQJjQzpTO
Implement endpoint logic
Endpoint-powered Flows should avoid using the endpoint when it is not needed. Avoiding the endpoint reduces latency for consumers and simplifies the development of the Flow.
Your endpoint receives requests in the following cases:
User opens the flow:
If flow_action field in the parameters that you pass to the Cloud API when sending a flow message is data_exchange;
See Data Exchange Request for details.
Tip: If the first screen of your flow does not have any parameters or the parameters are known when the message is sent, omit flow_action to avoid calling your endpoint. You can supply parameters by using the flow_action_payload.data message field instead.
User submits the screen:
If name attribute specified inside on-click-action field in Flow JSON is data_exchange;
See Data Exchange Request for details.
Tip: If the next screen and its data are known already, set the on-click-action name to navigate to avoid calling your endpoint.
User presses back button on the screen:
If refresh_on_back attribute specified in Flow JSON for the screen is true;
See Data Exchange Request for details.
Tip: If custom behavior when pressing the back button is not needed, omit refresh_on_back to avoid calling your endpoint.
User changes the value of a component:
If on-select-action for the component is defined in Flow JSON.
Your endpoint replied with invalid content to the previous request (for example, a required field was missing). In this case, the consumer client sends an asynchronous error notification request:
See Error Notification Request.
Periodical health check from WhatsApp:
See Health Check Request
Data exchange request
Data exchange request is used to query the name of the next screen and data required to render it. The decrypted payload of the data exchange request has the following format.
Sample Data Exchange Request Payload
{
    "version": "<VERSION>",
    "action": "<ACTION_NAME>",
    "screen": "<SCREEN_NAME>",
    "data": {
      "prop_1": "value_1",
       …
      "prop_n": "value_n"
    },
   "flow_token": "<FLOW-TOKEN>"
}
Parameter	Description
version
string
Required. Value must be set to 3.0.
screen
string
Required. If action is set to INIT or BACK, this field may not be populated. (Note: “SUCCESS” is a reserved name and no screens can use it.)
action
string
Required. Defines the type of the request. For a data exchange request, the value depends on what triggered it:
INIT if the request is triggered when opening the Flow
BACK if the request is triggered when pressing “back”
data_exchange if the request is triggered when submitting the screen
data
object
Required. An object passing arbitrary key-value data as a JSON object. If action is set to INIT or BACK, this field may not be populated.
<key> string, boolean, number, object, array - <value>
flow_token
string
Required. A Flow token generated and sent by you as part of the Flow message.
The flow token is similar to a session identifier commonly used in web applications. Generate it using established best practices (for example, it should not be predictable) to ensure the security of data exchanges with an endpoint.
flow_token_signature
string
Please note that flow_token_signature will only be sent with flows version >= 7.3 and data_api_version >=4.0.
A Flow token signature is generated and sent by flows as part of the data exchange request payload.
The flow_token_signature is a JSON Web Token (JWT) created by flows to securely sign the flow token using the Meta app secret as the secret key. You can choose to use this signature to verify the authenticity of the flow token. (see Flow token Signature for more details)
After the request is received and decrypted, your business logic processes the request and determines which screen and data is to be sent back to the WhatsApp client. If the user needs to be redirected to the next screen, next screen response payload should be sent. If the flow needs to be terminated (for example, because it is complete), final response payload should be sent.
Next Screen Response Payload for Data Exchange Request
The following response payload is what the data channel needs to send back to the WhatsApp client during each data exchange, except the last one:
{
    "screen": "<SCREEN_NAME>",
    "data": {
      "property_1": "value_1",
       ...
      "property_n": "value_n",
      "error_message": "<ERROR-MESSAGE>"
    }
}
If the data channel cannot process the request due to bad input, handle it gracefully by including an optional error_message in the data object as part of the response.
This redirects the user to <SCREEN_NAME> and triggers a snackbar error with the error_message present.
Parameter	Description
screen
string
Required. The screen to be rendered once the data exchange is complete.
data
object
Required. A JSON object of properties and their values to render the screen after data exchange is complete.
error_message string – If the WhatsApp client sends you a bad request, define the error message here.
<key> string, boolean, number, object, array – <value>: A property and its respective value which can be referenced in screen layout in Flow JSON.
Final Response Payload
To trigger flow completion, send the following response to the data exchange request:
{
    "screen": "SUCCESS",
    "data": {
        "extension_message_response": {
            "params": {
                "flow_token": "<FLOW_TOKEN>",
                "optional_param1": "<value1>",
                "optional_param2": "<value2>"
            }
        }
    }
}
Parameter	Description
screen
string
Value must be SUCCESS
data.extension_message_response.params
object
A JSON with data which will be included to the flow completion message (see Response Message Webhook for more details)
data.extension_message_response.params.flow_token
string
Required. Flow token generated by a business signifying a session or a user flow
As a result, flow will be closed and a flow response message will be sent to the chat. See Response Message Webhook for additional details.
It is highly recommended that you manually send a summary message to the chat with consumer in response, such as the one below:
Flow completion response message displayed in WhatsApp chat
If you need parameters from the data channel for the message content, you can send them in the params field in addition to flow_token. All these parameters are forwarded to the messages webhook.
Error notification request
If you send a bad response payload to the WhatsApp client, you receive a payload detailing the error and the error type. This provides you more visibility on failed client interactions so you can respond appropriately.
Sample Error Notification Request Payload
{
    "version": "<VERSION>",
    "flow_token": "<FLOW-TOKEN>",
    "action": "data_exchange | INIT",
    "data": {
        "error": "<ERROR-KEY>",
        "error_message": "<ERROR-MESSAGE>"
    }
}
Parameter	Description
version
string
Required. 3.0
screen
string
Required. The screen name where the bad intermediate response payload was sent.
flow_token
string
Required. A flow token generated by your business
action
string
Required. Either "data_exchange" or "INIT".
data
object
Required.data object representing the error.
data.error string – The error code for the invalid payload.
data.error_message string – The error message associated with the error code.
Error Notification Response Payload
Send the following response payload to indicate that error notification was acknowledged:
{
    "data": {
        "acknowledged": true
    }
}
Health check request
Endpoints should be able to respond to health check requests. WhatsApp may periodically send health check requests to the endpoints used by published flows.
Sample Health Check Request Payload
{
    "version": "3.0",
    "action": "ping"
}
You should generate the following response payload:
Health Check Response Payload
{
    "data": {
        "status": "active"
    }
}
Request signature validation
When creating your app, decide who owns it and the endpoint, whether it is you or the Solution Partner. To prevent sharing the app secret, the owners must be the same for both to use the app secret to validate the payload.
You can verify that request is coming from Meta by checking signature which is generated using an app secret from the app connected to the flow. The signature is inferred from the user token when the flow is created through API, or selected manually in the Flow Builder when endpoint is added to the flow.
Signature and Header Format
Meta signs all endpoint requests with a SHA256 signature and includes the signature in the request’s X-Hub-Signature-256 header, preceded with sha256=.
To validate the signature:
Generate a SHA256 signature using the payload and your app secret.
Compare your signature to the signature in the X-Hub-Signature-256 header (everything after sha256=). If the signatures match, the payload is genuine.
If validation fails, return an appropriate HTTP code. Please see the Business Endpoint Error Codes for more details.
Resetting the app secret
If you need to reset the app secret without any downtime and without turning off payload validation, you can use the following approach:
Allow the old app secret to continue generating the SHA256 signature for X hours
Temporary consider X-Hub-Signature-256 header to be correct if it can be validated using either old or new app secret.
After X hours (not earlier), consider the signature in the X-Hub-Signature-256 header correct only if it can be validated using new app secret.
Flow token signature
flow_token_signature for enhanced endpoint authentication
To enhance the security and integrity of flow interactions, Meta provides a parameter called flow_token_signature. This signature allows businesses to verify the authenticity of the flow token received in the message payload.
What is flow_token_signature?
The flow_token_signature is a JSON Web Token (JWT) created by flows to securely sign the flow token using the Meta app secret as the secret key. This JWT includes a header specifying the signing algorithm (HS256), a payload containing the flow token. It enables businesses to verify the authenticity and integrity of the flow token received in the message payload, ensuring the token has not been tampered with during transmission.
How to use?
The flow_token_signature is a parameter sent by flows and included in the data exchange request payload. Businesses can choose to use this signature to verify the authenticity of the flow token. To do so, businesses need to decode and verify the JWT using the Meta app secret, which is known to them. Once decoded, businesses can confirm that the flow_token value inside the token matches the expected value, ensuring the token has not been tampered with during transmission.
Request decryption and encryption
The incoming request body is encrypted. Decrypt it first, then encrypt the server response before returning it to the client.
You can find code examples of decryption/encryption in various programming languages in the Code Examples section.
For data_api_version “3.0” you should follow the instructions below to decrypt request payload:
extract payload encryption key from encrypted_aes_key field:
decode base64-encoded field content to byte array;
decrypt resulting byte array with the private key corresponding to the uploaded public key using RSA/ECB/OAEPWithSHA-256AndMGF1Padding algorithm with SHA256 as a hash function for MGF1;
as a result, you’ll get a 128-bit payload encryption key.
decrypt request payload from encrypted_flow_data field:
decode base64-encoded field content to get encrypted byte array;
decrypt encrypted byte array using AES-GCM algorithm, payload encryption key and initialization vector passed in initial_vector field (which is base64-encoded as well and should be decoded first). Note that the 128-bit authentication tag for the AES-GCM algorithm is appended to the end of the encrypted array.
result of above step is UTF-8 encoded clear request payload.
For data_api_version “3.0” you should follow the instructions below to encrypt the response:
encode response payload string to response byte array using UTF-8
prepare initialization vector for response encryption by inverting all bits of the initialization vector used for request payload encryption (XOR each byte with 0xFF)
encrypt response byte array using AES-GCM algorithm with the following parameters:
secret key - payload encryption key from request decryption stage
initialization vector for response encryption from above step
empty AAD (additional authentication data) - many libraries assume this by default, check the documentation of the library in use
128-bit (16 byte) length for authentication tag - many libraries assume this by default, check the documentation of the library in use
append authentication tag generated during encryption to the end of the encryption result
encode the whole output as base64 string and send it in the HTTP response body as plain text
Handling decryption errors
If you can’t decrypt a request, you should send appropriate HTTP response code to force mobile client to re-download public key and retry the query. See endpoint error codes for additional details.
Code examples
A full example of a Node.js endpoint server is available here. Below are some examples demonstrating how request encryption/decryption can be implemented in different languages.
The below code examples are only meant to demonstrate the encryption/decryption implementation and are not production ready.
Python Django example
Here’s a full code sample to handle a request with decryption/encryption in Python with Django framework. Note that the response is sent as a plain text string.
import json
import os
from base64 import b64decode, b64encode
from cryptography.hazmat.primitives.asymmetric.padding import OAEP, MGF1, hashes
from cryptography.hazmat.primitives.ciphers import algorithms, Cipher, modes
from cryptography.hazmat.primitives.serialization import load_pem_private_key
from django.http import HttpResponse
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt

# Load the private key string
PRIVATE_KEY = os.environ.get('PRIVATE_KEY')
# Example:
# '''-----BEGIN RSA PRIVATE KEY-----
# MIIE...
# ...
# ...AQAB
# -----END RSA PRIVATE KEY-----'''

@csrf_exempt
def data(request):
    try:
        # Parse the request body
        body = json.loads(request.body)

        # Read the request fields
        encrypted_flow_data_b64 = body['encrypted_flow_data']
        encrypted_aes_key_b64 = body['encrypted_aes_key']
        initial_vector_b64 = body['initial_vector']

        decrypted_data, aes_key, iv = decrypt_request(
            encrypted_flow_data_b64, encrypted_aes_key_b64, initial_vector_b64)
        print(decrypted_data)

        # Return the next screen & data to the client
        response = {
            "screen": "SCREEN_NAME",
            "data": {
                "some_key": "some_value"
            }
        }

        # Return the response as plaintext
        return HttpResponse(encrypt_response(response, aes_key, iv), content_type='text/plain')
    except Exception as e:
        print(e)
        return JsonResponse({}, status=500)

def decrypt_request(encrypted_flow_data_b64, encrypted_aes_key_b64, initial_vector_b64):
    flow_data = b64decode(encrypted_flow_data_b64)
    iv = b64decode(initial_vector_b64)

    # Decrypt the AES encryption key
    encrypted_aes_key = b64decode(encrypted_aes_key_b64)
    private_key = load_pem_private_key(
        PRIVATE_KEY.encode('utf-8'), password=None)
    aes_key = private_key.decrypt(encrypted_aes_key, OAEP(
        mgf=MGF1(algorithm=hashes.SHA256()), algorithm=hashes.SHA256(), label=None))

    # Decrypt the Flow data
    encrypted_flow_data_body = flow_data[:-16]
    encrypted_flow_data_tag = flow_data[-16:]
    decryptor = Cipher(algorithms.AES(aes_key),
                       modes.GCM(iv, encrypted_flow_data_tag)).decryptor()
    decrypted_data_bytes = decryptor.update(
        encrypted_flow_data_body) + decryptor.finalize()
    decrypted_data = json.loads(decrypted_data_bytes.decode("utf-8"))
    return decrypted_data, aes_key, iv

def encrypt_response(response, aes_key, iv):
    # Flip the initialization vector
    flipped_iv = bytearray()
    for byte in iv:
        flipped_iv.append(byte ^ 0xFF)

    # Encrypt the response data
    encryptor = Cipher(algorithms.AES(aes_key),
                       modes.GCM(flipped_iv)).encryptor()
    return b64encode(
        encryptor.update(json.dumps(response).encode("utf-8")) +
        encryptor.finalize() +
        encryptor.tag
    ).decode("utf-8")
Node.js Express example
Here’s a full code sample to handle a request with decryption/encryption in NodeJS with Express framework. Note that the response is sent as a plain text string.
import express from "express";
import crypto from "crypto";

const PORT = 3000;
const app = express();
app.use(express.json());

const PRIVATE_KEY = process.env.PRIVATE_KEY as string;
/*
Example:
-----BEGIN RSA PRIVATE KEY-----
MIIE...
...
...AQAB
-----END RSA PRIVATE KEY-----
*/

app.post("/data", async ({ body }, res) => {
  const { decryptedBody, aesKeyBuffer, initialVectorBuffer } = decryptRequest(
    body,
    PRIVATE_KEY,
  );

  const { screen, data, version, action } = decryptedBody;
  // Return the next screen & data to the client
  const screenData = {
    screen: "SCREEN_NAME",
    data: {
      some_key: "some_value",
    },
  };

  // Return the response as plaintext
  res.send(encryptResponse(screenData, aesKeyBuffer, initialVectorBuffer));
});

const decryptRequest = (body: any, privatePem: string) => {
  const { encrypted_aes_key, encrypted_flow_data, initial_vector } = body;

  // Decrypt the AES key created by the client
  const decryptedAesKey = crypto.privateDecrypt(
    {
      key: crypto.createPrivateKey(privatePem),
      padding: crypto.constants.RSA_PKCS1_OAEP_PADDING,
      oaepHash: "sha256",
    },
    Buffer.from(encrypted_aes_key, "base64"),
  );

  // Decrypt the Flow data
  const flowDataBuffer = Buffer.from(encrypted_flow_data, "base64");
  const initialVectorBuffer = Buffer.from(initial_vector, "base64");

  const TAG_LENGTH = 16;
  const encrypted_flow_data_body = flowDataBuffer.subarray(0, -TAG_LENGTH);
  const encrypted_flow_data_tag = flowDataBuffer.subarray(-TAG_LENGTH);

  const decipher = crypto.createDecipheriv(
    "aes-128-gcm",
    decryptedAesKey,
    initialVectorBuffer,
  );
  decipher.setAuthTag(encrypted_flow_data_tag);

  const decryptedJSONString = Buffer.concat([
    decipher.update(encrypted_flow_data_body),
    decipher.final(),
  ]).toString("utf-8");

  return {
    decryptedBody: JSON.parse(decryptedJSONString),
    aesKeyBuffer: decryptedAesKey,
    initialVectorBuffer,
  };
};

const encryptResponse = (
  response: any,
  aesKeyBuffer: Buffer,
  initialVectorBuffer: Buffer,
) => {
  // Flip the initialization vector
  const flipped_iv = [];
  for (const pair of initialVectorBuffer.entries()) {
    flipped_iv.push(~pair[1]);
  }
  // Encrypt the response data
  const cipher = crypto.createCipheriv(
    "aes-128-gcm",
    aesKeyBuffer,
    Buffer.from(flipped_iv),
  );
  return Buffer.concat([
    cipher.update(JSON.stringify(response), "utf-8"),
    cipher.final(),
    cipher.getAuthTag(),
  ]).toString("base64");
};

app.listen(PORT, () => {
  console.log(`App is listening on port ${PORT}!`);
});
PHP Slim example
Here’s a full code sample to handle a request with decryption/encryption in PHP with Slim framework. Note that the response is sent as a plain text string.
<?php
use Psr\Http\Message\ResponseInterface as Response;
use Psr\Http\Message\ServerRequestInterface as Request;
use phpseclib3\Crypt\RSA;
use phpseclib3\Crypt\AES;

require __DIR__ . '/vendor/autoload.php';

$app = Slim\Factory\AppFactory::create();
$app->post('/data', function (Request $request, Response $response) {
    $body = json_decode($request->getBody()->getContents(), true);

    $privatePem = getenv('PRIVATE_KEY');
    /*
    Example:
    -----BEGIN RSA PRIVATE KEY-----
    MIIE...
    ...
    ...AQAB
    -----END RSA PRIVATE KEY-----
    */
    $decryptedData = decryptRequest($body, $privatePem);

    // Return the next screen & data to client
    $screen = [
        "screen" => "SCREEN_NAME",
        "data" => [
            "some_key" => "some_value"
        ]
    ];
    $resBody = encryptResponse($screen, $decryptedData['aesKeyBuffer'], $decryptedData['initialVectorBuffer']);
    // Return the response as plaintext
    $response->getBody()->write($resBody);
    return $response;
});

function decryptRequest($body, $privatePem)
{
    $encryptedAesKey = base64_decode($body['encrypted_aes_key']);
    $encryptedFlowData = base64_decode($body['encrypted_flow_data']);
    $initialVector = base64_decode($body['initial_vector']);

    // Decrypt the AES key created by the client
    $rsa = RSA::load($privatePem)
        ->withPadding(RSA::ENCRYPTION_OAEP)
        ->withHash('sha256')
        ->withMGFHash('sha256');

    $decryptedAesKey = $rsa->decrypt($encryptedAesKey);
    if (!$decryptedAesKey) {
        throw new Exception('Decryption of AES key failed.');
    }

    // Decrypt the Flow data
    $aes = new AES('gcm');
    $aes->setKey($decryptedAesKey);
    $aes->setNonce($initialVector);
    $tagLength = 16;
    $encryptedFlowDataBody = substr($encryptedFlowData, 0, -$tagLength);
    $encryptedFlowDataTag = substr($encryptedFlowData, -$tagLength);
    $aes->setTag($encryptedFlowDataTag);

    $decrypted = $aes->decrypt($encryptedFlowDataBody);
    if (!$decrypted) {
        throw new Exception('Decryption of flow data failed.');
    }

    return [
        'decryptedBody' => json_decode($decrypted, true),
        'aesKeyBuffer' => $decryptedAesKey,
        'initialVectorBuffer' => $initialVector,
    ];
}

function encryptResponse($response, $aesKeyBuffer, $initialVectorBuffer)
{
    // Flip the initialization vector
    $flipped_iv = ~$initialVectorBuffer;

    // Encrypt the response data
    $cipher = openssl_encrypt(json_encode($response), 'aes-128-gcm', $aesKeyBuffer, OPENSSL_RAW_DATA, $flipped_iv, $tag);
    return base64_encode($cipher . $tag);
}

$app->run();
Java example
Here’s a full code sample to handle a request with decryption/encryption in Java 8+ using simple-json library:
Please note that this example requires private key to be in unencrypted PKCS8 format, which is normally indicated by -----BEGIN PRIVATE KEY----- at the beginning of the file.
Depending on the way and exact software which you used to generate private key, you may need to convert it to the required format first.
For example, if your key is in PKCS#1 format (starts with -----BEGIN RSA PRIVATE KEY-----) or PKCS#8 encrypted format (starts with -----BEGIN ENCRYPTED PRIVATE KEY-----), you can use the following command to convert it to the unencrypted PKCS#8:
openssl pkcs8 -topk8 -inform PEM -outform PEM -nocrypt -in private.pem -out private_unencrypted_pkcs8.pem
package org.example;

import com.sun.net.httpserver.HttpExchange;
import com.sun.net.httpserver.HttpHandler;
import com.sun.net.httpserver.HttpServer;
import org.json.simple.JSONObject;
import org.json.simple.parser.JSONParser;

import javax.crypto.Cipher;
import javax.crypto.spec.GCMParameterSpec;
import javax.crypto.spec.OAEPParameterSpec;
import javax.crypto.spec.PSource;
import javax.crypto.spec.SecretKeySpec;
import java.io.File;
import java.io.IOException;
import java.io.InputStreamReader;
import java.io.OutputStream;
import java.net.InetSocketAddress;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.security.GeneralSecurityException;
import java.security.KeyFactory;
import java.security.interfaces.RSAPrivateKey;
import java.security.spec.MGF1ParameterSpec;
import java.security.spec.PKCS8EncodedKeySpec;
import java.util.Base64;

public class App {

    private static class DecryptionInfo {
        public final String clearPayload;
        public final byte[] clearAesKey;

        public DecryptionInfo(String clearPayload, byte[] clearAesKey) {
            this.clearPayload = clearPayload;
            this.clearAesKey = clearAesKey;
        }
    }

    private static final int AES_KEY_SIZE = 128;
    private static final String KEY_GENERATOR_ALGORITHM = "AES";
    private static final String AES_CIPHER_ALGORITHM = "AES/GCM/NoPadding";
    private static final String RSA_ENCRYPT_ALGORITHM = "RSA/ECB/OAEPWithSHA-256AndMGF1Padding";
    private static final String RSA_MD_NAME = "SHA-256";
    private static final String RSA_MGF = "MGF1";

    public static void main(String[] args) throws Exception {
        HttpServer server = HttpServer.create(new InetSocketAddress(3000), 0);
        server.createContext("/data", new EndpointHandler());
        server.setExecutor(null);
        server.start();
        System.out.print("Server started on " + server.getAddress());
    }

    static class EndpointHandler implements HttpHandler {
        @Override
        public void handle(HttpExchange t) throws IOException {
            String response;
            int responseCode;
            try {
                final JSONParser parser = new JSONParser();
                final JSONObject requestJson = (JSONObject) parser.parse(new InputStreamReader(t.getRequestBody(), StandardCharsets.UTF_8));
                final byte[] encrypted_flow_data = Base64.getDecoder().decode((String) requestJson.get("encrypted_flow_data"));
                final byte[] encrypted_aes_key = Base64.getDecoder().decode((String) requestJson.get("encrypted_aes_key"));
                final byte[] initial_vector = Base64.getDecoder().decode((String) requestJson.get("initial_vector"));
                final DecryptionInfo decryptionInfo = decryptRequestPayload(encrypted_flow_data, encrypted_aes_key, initial_vector);
                final JSONObject clearRequestData = (JSONObject) parser.parse(decryptionInfo.clearPayload);
                final String clearResponse = String.format("{\"screen\":\"SCREEN_NAME\",\"data\":{\"some_key\":\"some_value\"}}");
                response = encryptAndEncodeResponse(clearResponse, decryptionInfo.clearAesKey, flipIv(initial_vector));
                responseCode = 200;
            } catch (Exception ex) {
                response = "Processing error: " + ex.getMessage();
                responseCode = 500;
            }
            t.getResponseHeaders().add("Content-Type", "text/plain; charset=UTF-8");
            final byte[] responseBytes = response.getBytes();
            t.sendResponseHeaders(responseCode, responseBytes.length);
            OutputStream os = t.getResponseBody();
            os.write(response.getBytes());
            os.close();
        }
    }

    private static DecryptionInfo decryptRequestPayload(byte[] encrypted_flow_data, byte[] encrypted_aes_key, byte[] initial_vector) throws Exception {
        final RSAPrivateKey privateKey = readPrivateKeyFromPkcs8UnencryptedPem(System.getenv("ENDPOINT_PRIVATE_KEY_FILE_PATH"));
        final byte[] aes_key = decryptUsingRSA(privateKey, encrypted_aes_key);
        return new DecryptionInfo(decryptUsingAES(encrypted_flow_data, aes_key, initial_vector), aes_key);
    }

    private static String decryptUsingAES(final byte[] encrypted_payload, final byte[] aes_key, final byte[] iv) throws GeneralSecurityException {
        final GCMParameterSpec paramSpec = new GCMParameterSpec(AES_KEY_SIZE, iv);
        final Cipher cipher = Cipher.getInstance(AES_CIPHER_ALGORITHM);
        cipher.init(Cipher.DECRYPT_MODE, new SecretKeySpec(aes_key, KEY_GENERATOR_ALGORITHM), paramSpec);
        final byte[] data = cipher.doFinal(encrypted_payload);
        return new String(data, StandardCharsets.UTF_8);
    }

    private static byte[] decryptUsingRSA(final RSAPrivateKey privateKey, final byte[] payload) throws GeneralSecurityException {
        final Cipher cipher = Cipher.getInstance(RSA_ENCRYPT_ALGORITHM);
        cipher.init(Cipher.DECRYPT_MODE, privateKey, new OAEPParameterSpec(RSA_MD_NAME, RSA_MGF, MGF1ParameterSpec.SHA256, PSource.PSpecified.DEFAULT));
        return cipher.doFinal(payload);
    }

    private static RSAPrivateKey readPrivateKeyFromPkcs8UnencryptedPem(String filePath) throws Exception {
        final String prefix = "-----BEGIN PRIVATE KEY-----";
        final String suffix = "-----END PRIVATE KEY-----";
        String key = new String(Files.readAllBytes(new File(filePath).toPath()), StandardCharsets.UTF_8);
        if (!key.contains(prefix)) {
            throw new IllegalStateException("Expecting unencrypted private key in PKCS8 format starting with " + prefix);
        }
        String privateKeyPEM = key.replace(prefix, "").replaceAll("[\\r\\n]", "").replace(suffix, "");
        byte[] encoded = Base64.getDecoder().decode(privateKeyPEM);
        KeyFactory keyFactory = KeyFactory.getInstance("RSA");
        PKCS8EncodedKeySpec keySpec = new PKCS8EncodedKeySpec(encoded);
        return (RSAPrivateKey) keyFactory.generatePrivate(keySpec);
    }

    private static String encryptAndEncodeResponse(final String clearResponse, final byte[] aes_key, final byte[] iv) throws GeneralSecurityException {
        final GCMParameterSpec paramSpec = new GCMParameterSpec(AES_KEY_SIZE, iv);
        final Cipher cipher = Cipher.getInstance(AES_CIPHER_ALGORITHM);
        cipher.init(Cipher.ENCRYPT_MODE, new SecretKeySpec(aes_key, KEY_GENERATOR_ALGORITHM), paramSpec);
        final byte[] encryptedData = cipher.doFinal(clearResponse.getBytes(StandardCharsets.UTF_8));
        return Base64.getEncoder().encodeToString(encryptedData);
    }

    private static byte[] flipIv(final byte[] iv) {
        final byte[] result = new byte[iv.length];
        for (int i = 0; i < iv.length; i++) {
            result[i] = (byte) (iv[i] ^ 0xFF);
        }
        return result;
    }
}
C# example
Here’s a full code sample to handle a request with decryption/encryption in C#. Note that the response is sent as a plain text string. View the full project code on GitHub.⁠
using System.Security.Cryptography;
using System.Text;
using System.Text.Json;
using Org.BouncyCastle.Crypto;
using Org.BouncyCastle.Crypto.Modes;
using Org.BouncyCastle.Crypto.Parameters;
using Org.BouncyCastle.Crypto.Engines;
using Org.BouncyCastle.OpenSsl;
using Org.BouncyCastle.Security;

var app = WebApplication.CreateBuilder(args).Build();
var PRIVATE_KEY = Environment.GetEnvironmentVariable("PRIVATE_KEY") ?? throw new InvalidOperationException("The environment variable 'PRIVATE_KEY' is not set.");
var PASSPHRASE = Environment.GetEnvironmentVariable("PASSPHRASE") ?? throw new InvalidOperationException("The environment variable 'PASSPHRASE' is not set.");

app.MapPost("/", (EndpointPayload body) =>
{
    var decrypted = EncryptionUtils.DecryptRequest(body.encrypted_aes_key, body.encrypted_flow_data, body.initial_vector, PRIVATE_KEY, PASSPHRASE);

    // Example to read decrypted fields
    var action = decrypted.decryptedBody.GetProperty("action").GetString();

    // Return the next screen & data to client
    var response = new { screen = "SCREEN_NAME", data = new { some_key = "some_value" } };
    var encryptedResponse = EncryptionUtils.EncryptResponse(response, decrypted.aesKeyBytes, decrypted.initialVectorBytes);

    // Return the response as plaintext
    return Results.Content(encryptedResponse, "text/plain");

})
.WithName("PostEndpointData");

app.Run();

record EndpointPayload(string encrypted_aes_key, string encrypted_flow_data, string initial_vector);

public class EncryptionUtils
{
    const int TAG_LENGTH = 16;

    public static (dynamic decryptedBody, byte[] aesKeyBytes, byte[] initialVectorBytes)
    DecryptRequest(string encryptedAesKey, string encryptedFlowData, string initialVector, string privatePem, string passphrase)
    {
        using (var rsa = RSA.Create())
        {
            // Load the private key from PEM
            var pemReader = new PemReader(new StringReader(privatePem), new PasswordFinder(passphrase));
            if (pemReader.ReadObject() is AsymmetricCipherKeyPair keyPair)
            {
                // Extract the private key parameters
                var privateKey = keyPair.Private as RsaPrivateCrtKeyParameters;
                if (privateKey == null)
                {
                    throw new CryptographicException("The provided PEM does not contain a valid RSA private key.");
                }

                // Convert Bouncy Castle RSA key parameters to .NET-compatible RSA parameters
                var rsaParams = DotNetUtilities.ToRSAParameters(privateKey);
                // Import into .NET RSA
                rsa.ImportParameters(rsaParams);
            }
            else
            {
                throw new CryptographicException("The provided PEM is not a valid encrypted PKCS#1 RSA private key.");
            }

            // Decrypt the AES key created by the client
            byte[] encryptedAesKeyBytes = Convert.FromBase64String(encryptedAesKey);
            byte[] aesKeyBytes = rsa.Decrypt(encryptedAesKeyBytes, RSAEncryptionPadding.OaepSHA256);

            // Decrypt the Flow data
            byte[] initialVectorBytes = Convert.FromBase64String(initialVector);
            byte[] flowDataBytes = Convert.FromBase64String(encryptedFlowData);
            byte[] plainTextBytes = new byte[flowDataBytes.Length - TAG_LENGTH];

            var cipher = new GcmBlockCipher(new AesEngine());
            var parameters = new AeadParameters(new KeyParameter(aesKeyBytes), TAG_LENGTH * 8, initialVectorBytes);
            cipher.Init(false, parameters);
            var offset = cipher.ProcessBytes(flowDataBytes, 0, flowDataBytes.Length, plainTextBytes, 0);
            cipher.DoFinal(plainTextBytes, offset);

            string decryptedJsonString = Encoding.UTF8.GetString(plainTextBytes);
            dynamic decryptedBody = JsonSerializer.Deserialize<dynamic>(decryptedJsonString);
            return (decryptedBody: decryptedBody, aesKeyBytes: aesKeyBytes, initialVectorBytes: initialVectorBytes);
        }
    }

    public static string EncryptResponse(dynamic response, byte[] aesKeyBytes, byte[] initialVectorBytes)
    {
        // Flip the initialization vector
        byte[] flippedIV = initialVectorBytes.Select(b => (byte)~b).ToArray();

        // Encrypt the response data
        string jsonResponse = JsonSerializer.Serialize(response);
        byte[] dataToEncrypt = Encoding.UTF8.GetBytes(jsonResponse);

        var cipher = new GcmBlockCipher(new AesEngine());
        var cipherParameters = new AeadParameters(new KeyParameter(aesKeyBytes), TAG_LENGTH * 8, flippedIV);

        // Encrypt the data
        cipher.Init(true, cipherParameters);
        byte[] encryptedDataBytes = new byte[cipher.GetOutputSize(dataToEncrypt.Length)];
        var offset = cipher.ProcessBytes(dataToEncrypt, 0, dataToEncrypt.Length, encryptedDataBytes, 0);
        cipher.DoFinal(encryptedDataBytes, offset);

        // Get the authentication tag
        byte[] authTag = new byte[TAG_LENGTH];
        Array.Copy(encryptedDataBytes, encryptedDataBytes.Length - TAG_LENGTH, authTag, 0, TAG_LENGTH);

        // Concatenate encrypted data and auth tag, then return as base64
        byte[] encryptedResponse = new byte[encryptedDataBytes.Length - TAG_LENGTH + TAG_LENGTH];
        Array.Copy(encryptedDataBytes, 0, encryptedResponse, 0, encryptedDataBytes.Length - TAG_LENGTH);
        Array.Copy(authTag, 0, encryptedResponse, encryptedDataBytes.Length - TAG_LENGTH, TAG_LENGTH);
        return Convert.ToBase64String(encryptedResponse);
    }
}

// Helper class for providing a password to the PemReader
public class PasswordFinder : IPasswordFinder
{
    private readonly char[] _password;

    public PasswordFinder(string password)
    {
        _password = password.ToCharArray();
    }

    public char[] GetPassword()
    {
        return _password;
    }
}
Go example
Here’s a full code sample to handle a request with decryption/encryption in Go. Note that the response is sent as a plain text string.View the full project code on GitHub.⁠
package main

import (
  "crypto/aes"
  "crypto/cipher"
  "crypto/rand"
  "crypto/rsa"
  "crypto/sha256"
  "crypto/x509"
  "encoding/base64"
  "encoding/json"
  "encoding/pem"
  "errors"
  "fmt"
  "log"
  "os"

  "github.com/gin-gonic/gin"
)

const nonceSize = 16

type endpointPayload struct {
  EncryptedAESKey   string `json:"encrypted_aes_key"`
  EncryptedFlowData string `json:"encrypted_flow_data"`
  InitialVector     string `json:"initial_vector"`
}

type decryptionResult struct {
  DecryptedBody      map[string]interface{}
  AESKeyBytes        []byte
  InitialVectorBytes []byte
}

func main() {
  privateKey := os.Getenv("PRIVATE_KEY")
  passphrase := os.Getenv("PASSPHRASE")
  if privateKey == "" || passphrase == "" {
    log.Fatal("Environment variables 'PRIVATE_KEY' and 'PASSPHRASE' are required.")
  }

  r := gin.Default()
  r.POST("/", func(c *gin.Context) {
    encryptedResponse, err := processRequest(c, privateKey, passphrase)
    if err != nil {
      log.Print(err)
      c.String(500, "Internal Server Error")
      return
    }
    // Return encrypted response as plain text
    c.String(200, encryptedResponse)
  })
  r.Run(":3000")
}

func processRequest(c *gin.Context, privateKey string, passphrase string) (string, error) {
  var payload endpointPayload
  if err := c.ShouldBindJSON(&payload); err != nil {
    return "", err
  }

  // Decrypt the request data
  decrypted, err := decryptRequest(payload.EncryptedAESKey, payload.EncryptedFlowData, payload.InitialVector, privateKey, passphrase)
  if err != nil {
    return "", err
  }

  // Access decrypted fields
  action, ok := decrypted.DecryptedBody["action"].(string)
  if ok {
    fmt.Printf("Action: %s\n", action)
  }

  // Create a response object
  response := map[string]interface{}{
    "screen": "SCREEN_NAME",
    "data":   map[string]string{"some_key": "some_value"},
  }

  // Encrypt the response
  encryptedResponse, err := encryptResponse(response, decrypted.AESKeyBytes, decrypted.InitialVectorBytes)
  if err != nil {
    return "", err
  }

  return encryptedResponse, nil
}

func decryptRequest(encryptedAESKey string, encryptedFlowData string, initialVector string, privatePem string, passphrase string) (decryptionResult, error) {
  // Parse the private key
  block, _ := pem.Decode([]byte(privatePem))
  if block == nil || !x509.IsEncryptedPEMBlock(block) {
    return decryptionResult{}, errors.New("invalid PEM format or not encrypted")
  }

  decryptedKey, err := x509.DecryptPEMBlock(block, []byte(passphrase))
  if err != nil {
    return decryptionResult{}, err
  }

  privateKey, err := x509.ParsePKCS1PrivateKey(decryptedKey)
  if err != nil {
    return decryptionResult{}, err
  }

  // Decrypt the AES key
  encryptedAESKeyBytes, _ := base64.StdEncoding.DecodeString(encryptedAESKey)
  aesKeyBytes, err := rsa.DecryptOAEP(sha256.New(), rand.Reader, privateKey, encryptedAESKeyBytes, nil)
  if err != nil {
    return decryptionResult{}, err
  }

  // Decrypt the Flow data
  initialVectorBytes, _ := base64.StdEncoding.DecodeString(initialVector)
  flowDataBytes, _ := base64.StdEncoding.DecodeString(encryptedFlowData)

  blockCipher, err := aes.NewCipher(aesKeyBytes)
  if err != nil {
    return decryptionResult{}, err
  }

  gcm, err := cipher.NewGCMWithNonceSize(blockCipher, nonceSize)
  if err != nil {
    return decryptionResult{}, err
  }

  decryptedPlaintext, err := gcm.Open(nil, initialVectorBytes, flowDataBytes, nil)
  if err != nil {
    return decryptionResult{}, err
  }

  var decryptedBody map[string]interface{}
  if err := json.Unmarshal(decryptedPlaintext, &decryptedBody); err != nil {
    return decryptionResult{}, err
  }

  return decryptionResult{
    DecryptedBody:      decryptedBody,
    AESKeyBytes:        aesKeyBytes,
    InitialVectorBytes: initialVectorBytes,
  }, nil
}

func encryptResponse(response map[string]interface{}, aesKeyBytes, initialVectorBytes []byte) (string, error) {
  // Flip the initialization vector
  flippedIV := make([]byte, len(initialVectorBytes))
  for i, b := range initialVectorBytes {
    flippedIV[i] = ^b
  }

  // Encrypt the response
  jsonResponse, err := json.Marshal(response)
  if err != nil {
    return "", err
  }

  blockCipher, err := aes.NewCipher(aesKeyBytes)
  if err != nil {
    return "", err
  }

  gcm, err := cipher.NewGCMWithNonceSize(blockCipher, nonceSize)
  if err != nil {
    return "", err
  }

  encryptedData := gcm.Seal(nil, flippedIV, jsonResponse, nil)
  return base64.StdEncoding.EncodeToString(encryptedData), nil
}
NodeJS script demonstrating AES key encryption and decryption
This NodeJS code sample aims to give an approximate example of how encrypted_aes_key field is calculated and how it can be decrypted.
// demo encryption/decryption script
// put public key in public_key.pem file in the same folder as this script
// put private key in private_key.pem file in the same folder as this script
// run with: node <script-file-name>

import crypto from "crypto";
import fs from "fs";

const CLEAR_AES_KEY_STR = "<some-key-data>"
const PRIVATE_KEY_DATA = fs.readFileSync('private_key.pem', 'utf8');
const PUBLIC_KEY_DATA = fs.readFileSync('public_key.pem', 'utf8');

console.log("Clear key: " + CLEAR_AES_KEY_STR)

const encryptedAesKey = crypto.publicEncrypt(
  {
    key: PUBLIC_KEY_DATA,
    padding: crypto.constants.RSA_PKCS1_OAEP_PADDING,
    oaepHash: "sha256"
  }
  ,
  Buffer.from(CLEAR_AES_KEY_STR)
);

const encryptedAesKeyBase64 = Buffer.from(encryptedAesKey).toString('base64');

console.log("Encrypted base64 key: " + encryptedAesKeyBase64)

const decryptedAesKey = crypto.privateDecrypt(
  {
    key: crypto.createPrivateKey({
      key: PRIVATE_KEY_DATA,
      format: 'pem',
      type: 'pkcs1',//ignored if format is pem
      passphrase: '<passphrase>'
    }),
    padding: crypto.constants.RSA_PKCS1_OAEP_PADDING,
    oaepHash: "sha256",
  },
  Buffer.from(encryptedAesKeyBase64, "base64"),
);

console.log("Decrypted key: " + decryptedAesKey)
if (decryptedAesKey.toString() === CLEAR_AES_KEY_STR) {
  console.log("Success, keys match!")
} else {
  console.log("Failed, keys do not match!")
}

-----------------------------

Flows Templates - WhatsApp Flows
Updated: Jun 16, 2026
You can quickly build WhatsApp Flow in the playground and send it as a template message, for example as part of a marketing campaign. Or you can create a WhatsApp Flow and send it either as a normal message.
To read more about message types, limits, and timing, see Send messages.
To send the Flow as a template, first you need to create a template. Here is an example request:
curl -i -X POST \
https://graph.facebook.com/v16.0/<waba-id>/message_templates \
-H 'Authorization: Bearer TOKEN' \
-H 'Content-Type: application/json' \
-d'
{
  "name": "example_template_name",
  "language": "en_US",
  "category": "MARKETING",
  "components": [
    {
      "type": "body",
      "text": "This is a flows as template demo"
    },
    {
      "type": "BUTTONS",
      "buttons": [
        {
          "type": "FLOW",
          "text": "Sign up",
          "flow_action": "navigate",
          "navigate_screen": "WELCOME_SCREEN"
          "flow_json" : "{    \"version\": \"3.1\",    \"screens\": [        {            \"id\": \"WELCOME_SCREEN\",            \"layout\": {                \"type\": \"SingleColumnLayout\",                \"children\": [                    {                        \"type\": \"TextHeading\",                        \"text\": \"Hello World\"                    },                    {                        \"type\": \"TextBody\",                        \"text\": \"Let\'s start building things!\"                    },                    {                        \"type\": \"Footer\",                        \"label\": \"Complete\",                        \"on-click-action\": {                            \"name\": \"complete\",                            \"payload\": {}                        }                    }                ]            },            \"title\": \"Welcome\",            \"terminal\": true,            \"success\": true,            \"data\": {}        }    ]}"
        }
      ]
    }
  ]
}'
Property	Type	Description
buttons.flow_json
String
The Flow JSON encoded as string. Specifies the layout of the flow to be attached to the Template. The Flow JSON can be quickly generated in the Flow playground. For full reference see Flow JSON documentation
Cannot be used if the flow_id attribute is provided. Only one of the parameters is allowed.
buttons.flow_id
String
id of a flow
Cannot be used if the flow_json attribute is provided. Only one of the parameters is allowed.
buttons.navigate_screen
String
Flow JSON screen name. Required if flow_action is navigate
buttons.flow_action
Enum
navigate or data_exchange. Default value is navigate
For more details, see the template components reference.
Sample response
{
  "id": "<template-id>",
  "status": "PENDING",
  "category": "MARKETING"
}
Ensure that your template passes all required reviews so that status is APPROVED instead of PENDING.
Now you can send a template message with a flow using the following request:
curl -X  POST \
 'https://graph.facebook.com/v16.0/FROM_PHONE_NUMBER_ID/messages' \
 -H 'Authorization: Bearer ACCESS_TOKEN' \
 -H 'Content-Type: application/json' \
 -d '{
  "messaging_product": "whatsapp",
  "recipient_type": "individual",
  "to": "PHONE_NUMBER",
  "type": "template",
  "template": {
    "name": "TEMPLATE_NAME",
    "language": {
      "code": "LANGUAGE_AND_LOCALE_CODE"
    },
    "components": [
      {
        "type": "button",
        "sub_type": "flow",
        "index": "0",
        "parameters": [
          {
            "type": "action",
            "action": {
              "flow_token": "FLOW_TOKEN",   //optional, default is "unused"
              "flow_action_data": {
                 ...
              }   // optional, json object with the data payload for the first screen
            }
          }
        ]
      }
    ]
  }
}'
Sample response
{
  "messaging_product": "whatsapp",
  "contacts": [
    {
      "input": "<phone-number>",
      "wa_id": "<phone-number>"
    }
  ],
  "messages": [
    {
      "id": "<message-id>"
    }
  ]
}

--------------------------

Send a Flow message - WhatsApp Flows
Updated: Jun 16, 2026
This guide describes the ways to send a Flow to users.
Prerequisites
You will need to verify your business and maintain a high message quality.
Postman collection
All the API requests mentioned below are documented in the Flows API postman collection⁠ which you can use to make API requests and generate code in different languages.
Business initiated messages
To send a business initiated message with a Flow, you can create and send a message template with a WhatsApp Flow attached to it. A new button type called FLOW is available. Use this type to specify the Flow to be sent with the message template.
To send a Flow message template you need to:
Create a message template with a Flow
Send a message template with a Flow
Create a message template with a Flow
You can quickly build a Flow in the playground and pass the Flow JSON in the message template creation request. Or you can specify the ID or name of an already published Flow.
Below is an example request to create a message template with a Flow, see this page for full reference:
Sample request
Sample request
curl -i -X POST \
  https://graph.facebook.com/<API_VERSION>/<WABA_ID>/message_templates \
  -H 'Authorization: Bearer TOKEN' \
  -H 'Content-Type: application/json' \
  -d'
  {
    "name": "example_template_name",
    "language": "en_US",
    "category": "MARKETING",
    "components": [
      {
        "type": "body",
        "text": "This is a flows as template demo"
      },
      {
        "type": "BUTTONS",
        "buttons": [
          {
            "type": "FLOW",
            "text": "Open flow!",
            "flow_id" : "<FLOW_ID>",
            // or
            "flow_name" : "<flow_name>",
            // or
            "flow_json" : "{\"version\":\"5.0\",\"screens\":[{\"id\":\"WELCOME_SCREEN\",\"layout\":{\"type\":\"SingleColumnLayout\",\"children\":[{\"type\":\"TextHeading\",\"text\":\"Hello World\"},{\"type\":\"Footer\",\"label\":\"Complete\",\"on-click-action\":{\"name\":\"complete\",\"payload\":{}}}]},\"title\":\"Welcome\",\"terminal\":true,\"success\":true,\"data\":{}}]}"
         }
        ]
      }
    ]
  }'
buttons object Parameters	Description
type string
Required. Button type. Default value is FLOW
text string
Required. Button label text. 25 characters maximum.
flow_id string
Required. The unique ID of the Flow. Cannot be used if flow_name or flow_json parameters are provided. Only one of these parameters is required.
flow_name string
Required. The name of the Flow. Supported in Cloud API only. The Flow ID is stored in the message template, not the name, so changing the Flow name will not affect existing message templates. Cannot be used if flow_id or flow_json parameters are provided. Only one of these parameters is required.
flow_json string
Required. The Flow JSON encoded as string with escaping. The Flow JSON specifies the content of the Flow. Supported in Cloud API only. Cannot be used if flow_id or flow_name parameters are provided. Only one of these parameters is required.
flow_action string
Default value is navigate. Either navigate or data_exchange.
nagivate_screen string
The unique ID of the Screen in the Flow. Default value is FIRST_ENTRY_SCREEN. Optional if flow_action is navigate.
Message templates can be created and sent in these languages.
Sample Response
{
  "id": "<TEMPLATE_ID>",
  "status": "PENDING",
  "category": "MARKETING"
}
Sample response
{
  "id": "<template-id>",
  "status": "PENDING",
  "category": "MARKETING"
}
Send template with flow
Ensure that your template passes all required reviews so that status is APPROVED instead of PENDING.
Now you can send a message template with a Flow using the request below
Sample request
curl -X  POST \
 'https://graph.facebook.com/v16.0/FROM_PHONE_NUMBER_ID/messages' \
 -H 'Authorization: Bearer ACCESS_TOKEN' \
 -H 'Content-Type: application/json' \
 -d '{
  "messaging_product": "whatsapp",
  "recipient_type": "individual",
  "to": "PHONE_NUMBER",
  "type": "template",
  "template": {
    "name": "TEMPLATE_NAME",
    "language": {
      "code": "LANGUAGE_AND_LOCALE_CODE"
    },
    "components": [
      {
        "type": "button",
        "sub_type": "flow",
        "index": "0",
        "parameters": [
          {
            "type": "action",
            "action": {
              "flow_token": "FLOW_TOKEN",   //optional, default is "unused"
              "flow_action_data": {
                 ...
              }   // optional, json object with the data payload for the first screen
            }
          }
        ]
      }
    ]
  }
}'
Sample response
{
  "messaging_product": "whatsapp",
  "contacts": [
    {
      "input": "<phone-number>",
      "wa_id": "<phone-number>"
    }
  ],
  "messages": [
    {
      "id": "<message-id>"
    }
  ]
}
User-initiated conversations
After you create a Flow, you can send it. You can send a Message with a Flow in a user-initiated conversation using a Message with a Call To Action (CTA). You send this message through the Cloud API with information specific to the Flow. Tapping the CTA button triggers the Flow.
Read more about message types, limits, and timing.
As mentioned earlier, a message with a Flow is not much different from other types of messages. A Flow message uses the existing APIs, which are described on the following pages:
Cloud API Interactive Messages documentation page describes how to send Interactive Messages with the Cloud API.
To send a message with a Flow, you can use a new type of the Interactive Object named flow with the following properties.
Interactive message parameters
Property	Type	Description
interactive.type
String
Value must be flow
interactive.action.name
String
Value must be flow
interactive.action.parameters.flow_message_version
String
Value must be 3.
interactive.action.parameters.flow_id
String
Unique ID of the Flow provided by WhatsApp.
Cannot be used with the flow_name parameter. Only one of these parameters is required.
interactive.action.parameters.flow_name
String
The name of the Flow that you created. Changing the Flow name will require updating this parameter to match the new name.
Cannot be used with the flow_id parameter. Only one of these parameters is required.
interactive.action.parameters.flow_cta
String
Text on the CTA button. For example: “Signup”
CTA text length is advised to be 30 characters or less (no emoji).
interactive.action.parameters.mode
String
The Flow can be in either draft or published mode. published is the default value for this field.
interactive.action.parameters.flow_token
String
Flow token that is generated by the business to serve as an identifier.
Default value is unused.
interactive.action.parameters.flow_action
String
navigate or data_exchange. Default value is navigate
interactive.action.parameters.flow_action_payload
String
Optional if flow_action is navigate. Should be omitted otherwise.
interactive.action.parameters.flow_action_payload.screen
String
The id of the first screen.
Default is FIRST_ENTRY_SCREEN
interactive.action.parameters.flow_action_payload.data
String
Optional. The input data for the first screen of the Flow. Must be a non-empty object.
Interactive messages parameter	Description
interactive object
The interactive message configuration. Available parameters:
action object – Required. Available parameters:
name string – Required. Value must be "flow".
parameters object – Required.
type string – Required. Value must be "flow".
action.parameter Parameter	Description
flow_action string
navigate or data_exchange. (Default value: navigate)
flow_action_payload object
Optional if flow_action is navigate. Should be omitted otherwise. Available values:
screen string – The ID of the screen displayed first. It needs to be an entry screen**. (Default value: FIRST_ENTRY_SCREEN)
data string – Optional input data for the first Screen of the Flow. If provided, this must be a non-empty JSON object serialized as a string.. (Default value: null)
flow_cta string
Text on the CTA button. For example: “Signup” CTA text length is advised to be 30 characters or less (no emoji).
flow_id string
Required if not using flow_name. Unique ID of the Flow provided by WhatsApp. Cannot be used with the flow_name parameter.
flow_message_version string
Value must be "3".
flow_name string
Required if not using flow_id. The name of the Flow that you created. Supported in Cloud API only. Changing the Flow name will require updating this parameter to match the new name. Cannot be used with the flow_id parameter.
flow_token string
Flow token that is generated by the business to serve as an identifier. (Default value: ‘unused’)
mode string
Status of the message. Can be draft or published. (Default value: published)
In case you edited published flow and now it is in the draft state, use “mode=draft” to send the current draft flow version, or “mode=published” (default value) to send the last published flow version.
See Flow JSON reference for entry screen details.
Cloud API Sample Request (with minimum parameters)
curl -X  POST \
 'https://graph.facebook.com/v18.0/FROM_PHONE_NUMBER/messages' \
 -H 'Authorization: Bearer ACCESS_TOKEN' \
 -H 'Content-Type: application/json' \
 -d '{
  "recipient_type": "individual",
  "messaging_product": "whatsapp",
  "to": "whatsapp-id",
  "type": "interactive",
  "interactive": {
    "type": "flow",
    "header": {
      "type": "text",
      "text": "Flow message header"
    },
    "body": {
      "text": "Flow message body"
    },
    "footer": {
      "text": "Flow message footer"
    },
    "action": {
      "name": "flow",
      "parameters": {
        "flow_message_version": "3",
        "flow_name": "appointment_booking_v1", //or flow_id
        "flow_cta": "Book!"
      }
    }
  }
}'
Cloud API Sample Request (with all parameters)
curl -X  POST \
 'https://graph.facebook.com/v18.0/FROM_PHONE_NUMBER/messages' \
 -H 'Authorization: Bearer ACCESS_TOKEN' \
 -H 'Content-Type: application/json' \
 -d '{
  "recipient_type": "individual",
  "messaging_product": "whatsapp",
  "to": "whatsapp-id",
  "type": "interactive",
  "interactive": {
    "type": "flow",
    "header": {
      "type": "text",
      "text": "Flow message header"
    },
    "body": {
      "text": "Flow message body"
    },
    "footer": {
      "text": "Flow message footer"
    },
    "action": {
      "name": "flow",
      "parameters": {
        "flow_message_version": "3",
        "flow_token": "AQAAAAACS5FpgQ_cAAAAAD0QI3s.",

        "flow_name": "appointment_booking_v1",
        //or
        "flow_id": "123456",

        "flow_cta": "Book!",
        "flow_action": "navigate",
        "flow_action_payload": {
          "screen": "<SCREEN_NAME>",
          "data": "{\"product_name\":\"name\",\"product_description\":\"description\",\"product_price\":100}"
        }
      }
    }
  }
}'
Sample Response
{
  "contacts": [
    {
      "Input": "+447385946746",
      "wa_id": "47385946746"
    }
  ],
  "messages": [
    {
      "id": "gHTRETHRTHTRTH-av4Y"
    }
  ],
  "meta": {
    "api_status": "stable",
    "version": "2.44.0.27"
  }
}

---------------------------------

Flow Health and Monitoring
Updated: Jun 16, 2026
It is important to monitor your Flow’s health and address any problems as they are discovered by WhatsApp. In order to do this, subscribe to and monitor the flow webhooks.
You will receive multiple alert webhooks before the Flow becomes Throttled or Blocked. See Quality system overview below for more information.
Flow health and monitoring is only applicable to Flows that use data from your endpoint.
Quality system overview
WhatsApp monitors and sends alert webhooks related to the following metrics:
Endpoint or Client error rate
Endpoint latency
Endpoint availability
If any of these metrics deteriorate significantly, WhatsApp may throttle or block your Flow.
Flow state	Published	Throttled	Blocked
Restrictions
No restrictions
Sending of the Flow restricted to 10 messages per hour.
Sending and opening of the Flow is blocked.
Impact
No impact
Consumers will still be able to open previously received Flows and use them. However, the business will be limited to sending only 10 new Flow messages per hour.
Businesses will not be able to send any new Flow messages and consumers will not be able to open previously sent Flow messages.
Flow state diagram with bidirectional arrows between Published (green), Throttled (yellow) and Blocked (red)
When a Flow’s endpoint metrics begin deteriorating, the Flow status will first move to Throttled. Only if metrics deteriorate further is it moved to Blocked.
Once a Flow’s endpoint recovers, it will move first from Blocked to Throttled, and then from Throttled back to Published.
How to get your Flow back to a Published state
Review the webhook alerts you have received for the Flow and check the contents of the alert.
If you have received:
Latency alert
Improve the responsiveness of your endpoint (aim to return a response in less than 1 second).
Availability alert
Ensure that your endpoint is available continuously, and is reachable from the internet.
Check that your endpoint can correctly respond to health check ping requests.
Error rate alert
Review the errors listed in the alert and check the error codes reference guide for possible resolutions.
Once you have fixed your endpoint, WhatsApp monitoring automatically detects the changes and the Flow’s state is updated.
Publishing checks
Check	Details	How to resolve
Is there a phone number connected to WhatsApp Business account?
There needs to be verified phone number connected to WhatsApp Business account.
You need to add a phone number to your WhatsApp Business account before you can send or publish a flow.
Is a signed Flow’s public key uploaded to a phone number?
User needs to upload signed Flow public key to a phone number
You need to upload and sign a public key to a phone number before you can send or publish a Flow.
Is data channel URI set?
You need to set the data_channel_uri property before you can send or publish a Flow.
Does the Flow have an application linked to it?
You need to connect a Meta app to the Flow before you can publish it.
Does the Flow have a valid Flow JSON?
You need to verify that the Flow has a valid Flow JSON before publishing.
Are Flow JSON and Data API versions valid?
Versions could become frozen or expired.
You need to verify that you’re using valid versions before you publish a new Flow. You can check the list of currently available versions in the changelog.
Is an endpoint available and responding to health check requests?
You need to verify that the endpoint is available and that you’ve implemented a health check before publishing.
Is WhatsApp Business account subscribed to the Flows webhooks?
Flow webhooks are the main way you can find out about production issues affecting your customers.
You need to verify that your WhatsApp Business account is subscribed to Flows webhooks.


---------------------------

WhatsApp Flows best practices
Updated: Jun 28, 2026
These are guidelines to optimize both the WhatsApp Flows user and developer experience.
Setup
Flows shouldn’t be long
Users should enter flows aiming to complete a task as quickly as possible, with tasks taking no longer than 5 minutes to complete.
Don’t have more than one task per screen
Screens with too many tasks may look messy and overwhelm the user. If the flow needs the user to complete multiple tasks, split them across several screens.
Don’t use too many components per screen
Too many components will make your screens look messy and may overwhelm users. It will also take longer to load.
Build for caching
Once a user has completed a screen and moves onto the next, their information will be cached. If there are too many components on a single screen and the user exits the flow, they will lose all of this information, which could be frustrating for users.
Don't vs do comparison of a long booking form crammed onto one screen versus split across several screens
Use flows without the endpoint where the data channel is not required
Endpointless flows often offer better experience for consumers
Endpointless flows are faster to build and integrate
Endpointless flows allow for the dynamic data to be injected in them at the time of sending
Only use endpoint powered flows, when the live data is required while user completes a flow - for example, for ticket booking.
Prefer to make the first screen a data-channel-less to optimize flow opening
Use an endpoint only for the specific screens which require it and use a navigate action otherwise
Technical
Latency
In order to achieve the best latency:
Reduce the number of calls to third party platforms
Use asynchronous calls to slow third party platforms
Cache data to prevent re-fetching unchanged data
Requests to the WhatsApp Flows data endpoint time out after 10 seconds.
flow_token expiration management
Set flow token expiration to 2-3 days to give users more time to engage with flow messages after receiving them.
If that is not possible for security reasons, consider embedding a re-authentication mechanism in the flow, or set a user-friendly message for an invalid flow token error with the recommended action to receive a new flow message.
If you have a business requirement to limit the flow message flow time, the timing should start only once the flow message has been opened, which is when the data channel receives the INIT request.
Design
Call-to-actions (CTAs)
The CTA should always tell the user what will happen next or what task is being completed on each screen, for example Confirm booking.
Don't vs do comparison of a 'Your details' screen with a vague 'Done' CTA versus a clear 'Confirm booking' CTA
Capitalization
Use sentence case on screen titles, headings, and CTAs. Use consistent capitalization throughout each flow.
Don't vs do comparison of a booking details screen with inconsistent title-case labels versus consistent sentence case
Emojis
Always consider the context of the content when using emojis, such as:
Are they appropriate to use?
Will they add to the content?
Do they reflect the business brand?
Error handling
Communicate errors clearly to the user, including what has happened and how to resolve it.
Make sure validation rules are clearly communicated, such as if a user tries to enter a password that is not long enough.
If the flow is exchanging data with your endpoint and a screen becomes invalid (for example, appointment booking), take the user back to the previous screen rather than ending the flow.
Don't vs do comparison of vague form error messages versus errors that explain how to fix the input
Diverging flows
If you need to create a sub flow for certain use cases (for example, a forgot password flow), limit it to a maximum of 3 screens and always take the user back to the main flow and task at hand.
Three-screen reset password sub flow from Login to email entry to reset link sent, returning to login
Form quality
Always use the right components for specific actions, for example use the date picker to capture DOB.
If an input requires a lot of text, use the text area component and not the text input.
Questions and form labels must provide full clarity on what it is asking the user.
Forms or questions should be logically ordered, for example, first name, last name, and so on.
Make non-critical fields optional.
Sign up form annotated with the component used for each field: text, password, date picker, email, and text area
Formatting
Ensure that any information is correctly formatted for context, for example currency symbols, phone numbers, and dates.
Grammar and spelling
Always check the content in your flows before publishing.
Ensure you use consistent spelling and capitalization for certain terms.
Check your grammar such as ensuring sentences use full-stops.
Helper text
Helper text should provide clarity for users, for example, the correct format for a phone number, date input, or email address.
Create account screen with helper text under the ID, password, and date of birth fields explaining each input
Initiation flow
The chat should provide clarity
Users will choose to open a flow based on the clarity of the initiation messages. The exchange should feel conversational, providing context and clear task-focused actions for the user.
Users want to complete a task
The CTA must match the message content. It should be short and concise, telling the user what task they can expect to complete by opening the flow.
There should be no surprises
The first screen of the flow should mirror the action of the CTA. Any deviations from the task at hand will result in a bad experience for the user, resulting in them closing the flow.
WhatsApp chats with clear task-focused CTAs that open flows matching the initiation message, such as 'Book a table'
Login screens
Some flows may need login screens to complete tasks. However, there are factors to consider when including them in your flows.
Use only when necessary
Including a login screen may discourage some users, so try to only use them when absolutely necessary. If you do need one, set the expectations for users so it doesn’t come as a surprise.
Orientation within flow
Research has shown that login screens may confuse users within flows. Some people thought screens would take them to an external page, outside of WhatsApp. This may result in users losing track of where they are within the flow.
Users need to see the benefit of logging in
The placement of login screens is key. If they are too early in the flow, users will not be motivated to continue. Showing the benefits upfront will make users want to complete the flow. Aim to make the login screen one of the last steps before completion.
Navigation
Always set expectations for how long it will take to complete a task, for example, “It should only take a few minutes to complete.”
Help the user know where they are in the flow by using short, concise action-oriented screen titles, such as “Book appointment.”
Use screen titles to show progress where possible, for example, “Question 1 of 3.”
End the flow with a summary screen, especially if there have been multiple steps, so users can review and complete the task with clarity.
Opt-in
It should be clear what the user is consenting to.
You should try to include a “Read more” CTA which links to the relevant information, for example, Terms and Conditions.
Sign up screen with a Terms and Conditions opt-in checkbox and 'Read more' link opening the full terms screen
Options and lists
Keep it simple; use no more than 10 options per screen.
Only use dropdown options when there are 8 or more options.
Use a radio button if there is only one selection to make.
Use checkboxes if the user can select multiple options.
Always make the option at the top of the list the default selection.
Termination flow
Set expectations
The last screen should clearly tell the user what will happen when they end the flow. They will also want confirmation of their actions. Sending a summary message should make the user feel reassured.
Keep the size of the completion payload minimal
Include only user-input data in the Flow’s completion payload, and keep the payload size to a minimum. Avoid leveraging the completion payload to send base64 images.
Confirm flow completion
Respond to the user with a message when they submit a Flow. These messages should provide the user with information about next steps, and who they can get in touch with if they have any questions or if they want to edit or cancel a task.
As of Flows version 5.1, upon submitting a Flow, a user will be able to access a summary of their submitted data via the Flow response message UI. By default, all user-input data is included in the response message, with the exception of text entry fields of type password and passcode. Businesses have the option to specify which data fields contain sensitive information by leveraging the sensitive property. These fields will not appear in the response message. For more details on how to configure sensitive fields, please refer to our documentation.
Trust and support
The business logo (profile photo) should be simple and identifiable in the footer so the user knows and trusts the flow.
Add a CTA within your flow that enables your users to get in touch when needed. This can also be done in follow-up messages once the user has completed the flow.
Don't vs do comparison of a login footer with an unclear business name versus a recognizable verified business logo
Writing content
Make sure your content follows a simple, clear hierarchy using a heading, body, and captions
Do not repeat content unnecessarily, for example:
“Complete registration”
“Complete registration below”


-------------

Testing and Debugging Flows
Updated: Jul 2, 2026
WhatsApp Flows provides multiple options for developers to test and debug their flows before publishing.
To test and verify that a flow works as expected, you can use:
Interactive preview
Draft flow message
To debug any issues with the flow, developers can use:
Action tab in the Flow Builder
Endpoint health check
Test flow using the interactive preview
Interactive preview of a WhatsApp Flow in the Flow Builder Preview section
Interactive preview lets you test the flow throughout the development process. Interactive preview triggers the same actions as the real device would, and if the flow has an endpoint configured, the flow sends encrypted requests to the endpoint. To start interactive preview:
Navigate to the Flows page in WA Account Manager⁠ and click on any Flow.
Trigger the interactive preview by clicking on the settings menu in the Preview section of the Flow Builder and enabling the Interactive mode toggle.
In the modal that appears, select the phone number, enter any string as Flow token and choose how to Request data on first screen.
You can now interact and complete the flow in the preview. The Flow Builder logs each action in the Actions tab at the bottom of the editor where you can see more details. If the Flow is using an endpoint, each data_exchange action will trigger the request to the endpoint. The Actions tab also shows the full request and response.
Send draft flow to your device
Draft Flow message on a device showing the draft-mode warning banner
Before you publish your flow you can also send it and test it on a real device. Flow messages sent in draft mode show a warning banner on the device. Once a Flow is published, the device no longer shows this warning.
Ensure you first send a message from your test device to the sender number. This is to make sure that you are within the 24-hour customer service window to receive the message. Learn more about customer service windows.
Navigate to the Flows page in WA Account Manager⁠ and click on any Flow in Draft state.
In the Flow Builder select three dot menu in the top right corner of the screen and select Send option.
In the modal select Sender number from the list. As the Recipient phone number, enter the phone number of your test device.
Enter any string as a Flow token (learn more about the flow_token parameter), select the Request Data option (learn more about providing data for the first screen) and click on Send.
You should receive a message with a Flow attached to your device and be able to test the Flow.
Draft messages can also be sent via API by setting mode parameter to draft.
Debug flow actions using the Actions section of the Builder
Actions tab at the bottom of the Flow Builder code editor listing logged Flow actions
When you enable the Interactive preview, the Flow Builder logs each Flow action in the Actions tab at the bottom of the code editor.
Flows without endpoint
For Flows without an endpoint the Actions tab shows:
navigate actions including any data passed between the screens
back action when the user clicks the back button
complete action with the full payload submitted at the Flow completion
Flows with endpoint
For Flows with an endpoint the Actions tab shows all the actions:
init action with initial data returned by the endpoint
navigate actions including any data passed between the screens
data_exchange actions with HTTP status code, the unencrypted request sent to the endpoint, and the unencrypted response received from it.
back action when the user clicks the back button
complete action with the full payload submitted at the Flow completion
Debug endpoint configuration and encryption setup using health check
Endpoint health check results in the Flow Builder showing configuration, reachability, encryption, and payload checks
The health check allows users to verify that the endpoint health check ping request and encryption are working correctly.
Endpoint health check is accessible from the Flow Builder, from the three dot menu in the top right corner of the screen. Select Setup under the Endpoint section. In the modal select Health check step and click the Run Check button to trigger the check.
Health check triggers a ping against the provided endpoint URI and if there’s an error, the health check returns detailed error and resolution information.
It detects various issues such as:
Missing/incorrect configuration: It checks whether all the pre-requisites are set up correctly. For example, it checks whether the public key is uploaded, or whether the endpoint URI is set.
Endpoint not being reachable or responding correctly: It checks whether the provided endpoint URI is reachable from the internet, whether it is responsive, and whether it returns the expected status code.
Encryption: It checks whether the response is encrypted, whether it is encrypted with the correct key, and whether it is base64 encoded.
Payload: It checks whether the response payload is as expected.

------------------------

