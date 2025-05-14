from flask import Flask, render_template, request, jsonify, send_from_directory
import os
import requests  # Import the requests library
import uuid  # For generating unique filenames
import traceback # Import traceback
import base64

app = Flask(__name__, static_folder='.', static_url_path='') # Tell Flask to serve static files from the current directory

# Configure the Gemini API key from the environment variable
GOOGLE_API_KEY = os.environ.get("GOOGLE_API_KEY")

#GOOGLE_API_KEY = "YOUR_API_KEY" # Replace with your actual API key if not using environment variable
if not GOOGLE_API_KEY:
    raise ValueError(
        "GOOGLE_API_KEY environment variable not set.  "
        "Please set it before running the application."
    )

# Specify the Gemini model and API endpoint.
#MODEL_NAME = "gemini-2.0-flash-preview-image-generation"
MODEL_NAME = "gemini-2.0-flash-exp-image-generation"
API_BASE_URL = "https://generativelanguage.googleapis.com/v1beta/models"
API_ENDPOINT = f"{API_BASE_URL}/{MODEL_NAME}:generateContent"

# Output directory to save generated images.
OUTPUT_FOLDER = "generated_images"
if not os.path.exists(OUTPUT_FOLDER):
    os.makedirs(OUTPUT_FOLDER)


def generate_image_with_gemini(prompt):
    """
    Generates an image using the Gemini API with the requests library.

    Args:
        prompt (str): The text prompt to generate the image from.

    Returns:
        str: The filename of the saved image, or None on error.
    """
    try:
        # Construct the request payload.
        payload = {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig":{
                "responseModalities":["Text","Image"],
                
            }
        }

        # Add the API key to the request URL.
        params = {"key": GOOGLE_API_KEY}

        # Make the POST request to the Gemini API.
        print(f"Request Payload: {payload}")  # Debug: Print the payload
        print(f"Request Params: {params}")  # Debug: Print the parameters
        response = requests.post(API_ENDPOINT, json=payload, params=params)
        print(f"Response Status Code: {response.status_code}")
        response.raise_for_status()  # Raise an exception for bad status codes (4xx or 5xx)

        # Parse the JSON response.
        response_json = response.json()
        print(f"Full Response JSON: {response_json}")  # Debug: Print full JSON

        # Check for errors in the response.  This is crucial!
        if "error" in response_json:
            error_message = response_json["error"].get("message", "Unknown error from Gemini API")
            print(f"Gemini API Error: {error_message}")
            return None

        # Extract the image data from the response.
        # The provided JSON shows the image data is in:
        # response_json['candidates'][0]['content']['parts'][1]['inlineData']['data']
        if (
            "candidates" in response_json
            and response_json["candidates"]
            and len(response_json["candidates"]) > 0
            and "content" in response_json["candidates"][0]
            and "parts" in response_json["candidates"][0]["content"]
        ):
            parts = response_json["candidates"][0]["content"]["parts"]
            for part in parts:
                if "inlineData" in part and "data" in part["inlineData"]:
                    image_data = part["inlineData"]["data"]  # This is base64 encoded
                    # mime_type = part["inlineData"]["mimeType"] #useful
                    # Generate a unique filename.
                    filename = f"image_{uuid.uuid4().hex}.png" #or jpg
                    filepath = os.path.join(OUTPUT_FOLDER, filename)
                    # Decode base64 and write to file.
                    try:
                        with open(filepath, "wb") as f:
                            f.write(base64.b64decode(image_data))
                        return filename
                    except Exception as e:
                        print(f"Error saving image: {e}")
                        return None
        else:
            print("Error: Image data not found in Gemini API response.")
            print(f"Full response: {response_json}")
            return None

    except requests.exceptions.RequestException as e:
        print(f"Error making request to Gemini API: {e}")
        print(f"Full error: {e}")
        return None
    except (KeyError, ValueError, OSError) as e:
        print(f"Error processing Gemini API response: {e}")
        print(f"Full error: {traceback.format_exc()}")  # Print the traceback
        return None
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
        print(f"Full error: {traceback.format_exc()}")
        return None



@app.route("/", methods=["GET", "POST"])
def index():
    """
    Handles the main page of the app.
    """
    if request.method == "POST":
        prompt = request.form["prompt"]
        image_filename = generate_image_with_gemini(prompt)
        if image_filename:
            # Pass the filename to the template.  The template will construct the URL.
            return render_template("index.html", prompt=prompt, image_filename=image_filename)
        else:
            return render_template(
                "index.html", prompt=prompt, error="Failed to generate image."
            )
    return render_template("index.html")





@app.route('/generated_images/<filename>')
def serve_image(filename):
    """
    Serves the generated image files from the specified output folder.
    """
    return send_from_directory(OUTPUT_FOLDER, filename)



if __name__ == "__main__":
    app.run(debug=True)









#GOOGLE_API_KEY = "AIzaSyCODX26wsePmZg9RHQbdQNuk032vGqLrDQ"
