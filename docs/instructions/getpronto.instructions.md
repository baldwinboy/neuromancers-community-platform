# Documentation for REST API and TypeScript SDK
Get Pronto Documentation
------------------------

Welcome to the Get Pronto documentation. Here you'll find everything you need to help you start working with the Get Pronto asset hosting service as quickly as possible.

---

# Authentication - Get Pronto Documentation
Get Pronto uses API keys to authenticate requests. You can view and manage your API keys from your Get Pronto Dashboard.

Key Types
---------

Get Pronto provides two types of API keys, each designed for different use cases:


|                       |Secret Key pronto_sk_|Public Key pronto_pk_|
|-----------------------|---------------------|---------------------|
|Upload files           |Yes                  |Yes                  |
|List files             |Yes                  |No                   |
|Get file metadata      |Yes                  |No                   |
|Delete files           |Yes                  |No                   |
|Generate transform URLs|Yes                  |No                   |
|Safe for browser code  |No                   |Yes                  |


Getting Your API Key
--------------------

To access the Get Pronto API, you'll need an API key. Here's how to get one:

1.  Log in to your [Get Pronto Dashboard](https://app.getpronto.io/dashboard)
2.  Navigate to the **API Keys** section
3.  Click **Create New API Key**
4.  Choose **Secret Key** for server-side use or **Public Key** for browser/client-side use
5.  Give your key a name (e.g., "Development", "Production")
6.  Copy your new API key - **note that it will only be shown once**

Authenticating with the SDK
---------------------------

When using the Get Pronto SDK, provide your API key during client initialization. The SDK automatically detects the key type from the prefix:

### Server-side (Secret Key)

### Client-side (Public Key)

Authenticating REST API Requests
--------------------------------

For direct REST API requests, include your API key in the request headers:

All API requests must be made over HTTPS. Calls made over plain HTTP will fail.

### Request Headers



* Header: Authorization
  * Description: Your API key in the format: ApiKey YOUR_API_KEY
  * Required: Yes
* Header: Content-Type
  * Description: The content type of the request body (for POST/PUT requests)
  * Required: Conditional
* Header: Accept
  * Description: The format of the response you want to receive (defaults to application/json)
  * Required: No


API Key Security
----------------

Best practices for keeping your keys safe:

*   **Use public keys for browser code** — they can only upload files, so exposure is low-risk
*   **Keep secret keys server-side only** — store them in environment variables, never in client-side code or repositories
*   Use different keys for different environments (development, production)
*   Regenerate keys periodically

Next Steps
----------

Continue exploring our documentation with these related topics:

---

# Quick Start - Get Pronto Documentation
This guide will help you get started with Get Pronto's asset hosting service in just a few minutes. You'll learn how to set up your account, install the SDK, and perform basic file operations.

Step 1: Create an Account
-------------------------

1.  Visit [https://app.getpronto.io/signup](https://app.getpronto.io/signup) to create your Get Pronto account
2.  Complete the registration form with your information
3.  Verify your email address by clicking the link sent to your inbox
4.  Log in to your new account

Step 2: Get Your API Key
------------------------

1.  Navigate to the **API Keys** section in your dashboard
2.  Click **Create New API Key**
3.  Give your key a name (e.g., "Development")
4.  Copy your new API key and store it securely

**Important:** Your API key will only be shown once. Make sure to copy it to a secure location. For more information on API keys, see our [Authentication guide](https://www.getpronto.io/docs/getting-started/authentication).

Step 3: Install the SDK
-----------------------

Install the Get Pronto SDK using npm or yarn:

Step 4: Initialize the SDK Client
---------------------------------

Create and initialize a Get Pronto client with your API key. Use a **secret key** for server-side code or a **public key** for browser-side uploads:

Step 5: Upload Your First File
------------------------------

Now that you have the client set up, let's upload a file:

Step 6: List Your Files
-----------------------

Retrieve a list of your uploaded files:

Step 7: Transform an Image
--------------------------

Get Pronto allows you to transform images on-the-fly. Here's how to generate a URL for a resized image:

Complete Example
----------------

Here's a complete example that ties everything together:

Next Steps
----------

Continue exploring our documentation with these related topics:

---

# API Overview - Get Pronto Documentation
The Get Pronto API is organized around REST principles. It accepts JSON-encoded request bodies, returns JSON-encoded responses, and uses standard HTTP response codes.

Base URL
--------

All API requests should be made to the following base URL:

The API is versioned through the URL path. The current version is `v1`.

Authentication
--------------

Get Pronto uses API keys to authenticate requests. You must include your API key in the headers of all API requests. For detailed information about obtaining and managing API keys, see our [Authentication guide](https://www.getpronto.io/docs/getting-started/authentication).

**Important:** Keep your API keys secure and never share them in publicly accessible areas such as GitHub, client-side code, or public forums.

Request/Response Format
-----------------------

The API accepts and returns JSON data. Always include the following headers in your requests:

### Response Structure

Successful responses follow a standard format that includes the requested data and, where applicable, pagination information:

#### Pagination

For endpoints that return lists of items, the response includes pagination information:

Error Handling
--------------

Get Pronto uses conventional HTTP response codes to indicate the success or failure of API requests. In general:

*   2xx indicates success
*   4xx indicates an error that failed given the information provided
*   5xx indicates an error with Get Pronto's servers

### Error Response Format

When an error occurs, you'll receive a JSON response with an error message:

### Common Error Codes


|Status Code|Description                                            |
|-----------|-------------------------------------------------------|
|400        |Bad Request - Invalid parameters or request body       |
|401        |Unauthorized - Invalid or missing API key              |
|403        |Forbidden - Valid API key but insufficient permissions |
|404        |Not Found - Resource doesn't exist                     |
|429        |Too Many Requests - Rate limit exceeded                |
|500        |Internal Server Error - Something went wrong on our end|


Rate Limiting
-------------

To ensure stability and fair usage, Get Pronto implements rate limiting on API requests. Rate limit information is included in the response headers:

If you exceed the rate limit, you'll receive a `429 Too Many Requests` response. The response will include a `Retry-After` header indicating when you can resume making requests.

Next Steps
----------

Continue exploring our documentation with these related topics:

---

# Files API - Get Pronto Documentation
The Files API allows you to upload, list, retrieve, and delete files in your Get Pronto account. All file operations require authentication using your API key.

Step 1: Request Presigned URL
-----------------------------

Request a presigned URL for direct-to-storage upload. This is the first step of the upload flow.

### Endpoint

### Request Parameters


|Parameter     |Type  |Description                                    |
|--------------|------|-----------------------------------------------|
|filename      |String|Original filename                              |
|mimetype      |String|MIME type of the file                          |
|size          |Number|File size in bytes                             |
|customFilename|String|Optional. Custom filename for the uploaded file|
|folderName    |String|Optional. Folder name to upload into           |


### Example Request

### Response

Step 2: Upload to Storage
-------------------------

Upload the file directly to storage using the presigned URL from step 1.

### Endpoint

### Example Request

Step 3: Confirm Upload
----------------------

Confirm the upload completed successfully. This verifies the file in storage and creates the file record.

### Endpoint

### Request Parameters


|Parameter      |Type  |Description                      |
|---------------|------|---------------------------------|
|pendingUploadId|String|The pending upload ID from step 1|


### Example Request

### Response

List Files
----------

Retrieve a paginated list of files in your account.

### Endpoint

### Query Parameters


|Parameter|Type   |Description                           |
|---------|-------|--------------------------------------|
|page     |Integer|Page number (default: 1)              |
|pageSize |Integer|Items per page (default: 20, max: 100)|


### Example Request

### Response

Get File
--------

Retrieve metadata for a specific file by its ID.

### Endpoint

### Path Parameters


|Parameter|Type  |Description                      |
|---------|------|---------------------------------|
|id       |String|The unique identifier of the file|


### Example Request

### Response

Delete File
-----------

Permanently delete a file from your account.

### Endpoint

### Path Parameters


|Parameter|Type  |Description                                |
|---------|------|-------------------------------------------|
|id       |String|The unique identifier of the file to delete|


### Example Request

### Response

File Object
-----------

The file object contains the following properties:


|Parameter         |Type         |Description                                                |
|------------------|-------------|-----------------------------------------------------------|
|id                |String       |Unique identifier for the file                             |
|name              |String       |Original filename                                          |
|secureUrl         |String       |Authenticated URL for file access via the API              |
|secureThumbnailUrl|String       |Authenticated URL for thumbnail access                     |
|rawUrl            |String       |Direct storage URL for the file                            |
|type              |String       |Formatted file type (image, video, json, file)             |
|rawType           |String       |Raw MIME type of the file                                  |
|size              |String       |Human-readable file size (e.g., '1.5 MB')                  |
|rawSize           |Number       |File size in bytes                                         |
|updated           |String       |Human-readable time since last update (e.g., '2 hours ago')|
|rawUpdated        |String       |ISO 8601 timestamp of when the file was last updated       |
|folderId          |String | null|ID of the folder the file belongs to, or null              |


### Example File Object

Next Steps
----------

Continue exploring our documentation with these related topics:

---

# Images API - Get Pronto Documentation
The Images API allows you to serve and transform images on-the-fly. You can resize, crop, apply effects, and optimize images for different use cases.

Serve Image
-----------

Access and serve an image, with optional transformations applied on-the-fly.

### Endpoint

### Path Parameters


|Parameter|Type  |Description               |
|---------|------|--------------------------|
|path     |String|The path to the image file|


### Query Parameters


|Parameter|Type   |Description                                       |
|---------|-------|--------------------------------------------------|
|w        |Integer|Width in pixels (1-5000)                          |
|h        |Integer|Height in pixels (1-5000)                         |
|fit      |String |Resize mode: cover, contain, fill, inside, outside|
|q        |Integer|Quality (1-100)                                   |
|blur     |Number |Blur radius (0.3-1000)                            |
|sharp    |Boolean|Apply sharpening                                  |
|gray     |Boolean|Convert to grayscale                              |
|rot      |Integer|Rotation angle (-360 to 360)                      |
|border   |String |Format: 'width_hexcolor' (e.g., '5_FF0000')       |
|crop     |String |Format: 'x,y,width,height'                        |


### Example Request

The response will be the image data with appropriate content-type headers.

Generate Transform URL
----------------------

Generate a URL for an image with specified transformations.

### Endpoint

### Path Parameters


|Parameter|Type  |Description                       |
|---------|------|----------------------------------|
|id       |String|The unique identifier of the image|


### Request Body Parameters


|Parameter|Type   |Description                                       |
|---------|-------|--------------------------------------------------|
|w        |Integer|Width in pixels (1-5000)                          |
|h        |Integer|Height in pixels (1-5000)                         |
|fit      |String |Resize mode: cover, contain, fill, inside, outside|
|q        |Integer|Quality (1-100)                                   |
|blur     |Number |Blur radius (0.3-1000)                            |
|sharp    |Boolean|Apply sharpening                                  |
|gray     |Boolean|Convert to grayscale                              |
|rot      |Integer|Rotation angle (-360 to 360)                      |
|border   |String |Format: 'width_hexcolor' (e.g., '5_FF0000')       |
|crop     |String |Format: 'x,y,width,height'                        |
|format   |String |Output format (jpg, png, webp, etc)               |


### Example Request

### Response

Transformation Options
----------------------

The following transformations can be applied to images either via URL parameters or through the transform URL endpoint:

### Resize


|Parameter|Type   |Description                                                    |
|---------|-------|---------------------------------------------------------------|
|w, h     |Integer|Target dimensions (1-5000px)                                   |
|fit      |String |How image fits: cover (default), contain, fill, inside, outside|


Example: `w=800&h=600&fit=cover`

### Quality


|Parameter|Type   |Description              |
|---------|-------|-------------------------|
|q        |Integer|JPEG/WebP quality (1-100)|


Example: `q=90`

### Effects


|Parameter|Type   |Description             |
|---------|-------|------------------------|
|blur     |Number |Gaussian blur (0.3-1000)|
|sharp    |Boolean|Sharpen the image       |
|gray     |Boolean|Convert to grayscale    |


Example: `blur=5&sharp=true&gray=true`

### Rotation & Cropping


|Parameter|Type   |Description                        |
|---------|-------|-----------------------------------|
|rot      |Integer|Rotation angle (-360 to 360)       |
|crop     |String |Crop coordinates (x,y,width,height)|


Example: `rot=90&crop=100,100,500,500`

**Note:** Transformations are processed in the order they are specified. For example, if you apply both crop and resize, the image will be cropped first, then resized to the specified dimensions.

Next Steps
----------

Continue exploring our documentation with these related topics:

---

# Supported File Types - Get Pronto Documentation
Supported File Types & Formats
------------------------------

Get Pronto supports a wide range of file formats for storage and delivery. Image files additionally support transformations like resizing, format conversion, and optimization.

File Type Detection
-------------------

Get Pronto automatically detects file types using both file extensions and content analysis. When uploading files, you can optionally specify a MIME type to override the automatic detection:

Images
------

Max Size: `25MB`

Transformations: Supported

Static and animated image formats


|MIME Type    |Extensions                    |Notes                                  |
|-------------|------------------------------|---------------------------------------|
|image/jpeg   |.jpg, .jpeg, .jpe, .jif, .jfif|Supports quality optimization          |
|image/png    |.png                          |Supports transparency                  |
|image/gif    |.gif                          |Supports animation                     |
|image/webp   |.webp                         |Modern format with superior compression|
|image/svg+xml|.svg                          |Vector format                          |
|image/tiff   |.tiff, .tif                   |                                       |
|image/bmp    |.bmp                          |                                       |
|image/heic   |.heic                         |High-efficiency format                 |
|image/avif   |.avif                         |Next-gen format with best compression  |


Videos
------

Common video formats


|MIME Type       |Extensions |Notes                            |
|----------------|-----------|---------------------------------|
|video/mp4       |.mp4, .m4v |Most widely supported            |
|video/webm      |.webm      |Open format with good compression|
|video/ogg       |.ogv       |                                 |
|video/quicktime |.mov       |                                 |
|video/x-msvideo |.avi       |                                 |
|video/x-matroska|.mkv       |Container format                 |
|video/3gpp      |.3gp       |Mobile-optimized                 |
|video/x-ms-wmv  |.wmv       |                                 |
|video/mpeg      |.mpeg, .mpg|                                 |


Documents
---------

Text-based formats


|MIME Type       |Extensions|
|----------------|----------|
|application/json|.json     |
|text/plain      |.txt      |


Archives
--------

Compressed file formats


|MIME Type                   |Extensions|Notes                    |
|----------------------------|----------|-------------------------|
|application/zip             |.zip      |                         |
|application/x-zip-compressed|.zip      |Alternative ZIP MIME type|
|application/x-7z-compressed |.7z       |                         |
|application/x-rar-compressed|.rar      |                         |
|application/gzip            |.gz, .gzip|                         |
|application/x-tar           |.tar      |                         |


Image Format Optimization
-------------------------

When using image transformations, Get Pronto can automatically optimize the output format based on browser support and quality requirements. You can either specify a format explicitly or let the system choose the best format:

Next Steps
----------

Continue exploring our documentation with these related topics: