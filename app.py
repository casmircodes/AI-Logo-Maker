from flask import Flask, render_template, request, jsonify, send_from_directory
import os
import requests
import uuid
import traceback
import base64

app = Flask(__name__, static_folder='generated_images', static_url_path='/generated_images')

# Moved these variables to be passed explicitly or accessed via request.form
# global businessname
# global slogan
# global industry
# global main_prompt # This should be generated inside the route, not globally

# Configure the Gemini API key from the environment variable
GOOGLE_API_KEY = os.environ.get("GOOGLE_API_KEY")

if not GOOGLE_API_KEY:
    raise ValueError(
        "GOOGLE_API_KEY environment variable not set. "
        "Please set it before running the application."
    )

MODEL_NAME = "gemini-2.0-flash-exp-image-generation"
API_BASE_URL = "https://generativelanguage.googleapis.com/v1beta/models"
API_ENDPOINT = f"{API_BASE_URL}/{MODEL_NAME}:generateContent"

OUTPUT_FOLDER = "generated_images"
if not os.path.exists(OUTPUT_FOLDER):
    os.makedirs(OUTPUT_FOLDER)


def generate_image_with_gemini(prompt, num_images=4):
    """
    Generates multiple images using the Gemini API.

    Args:
        prompt (str): The text prompt to generate the image from.
        num_images (int): The number of images to generate.

    Returns:
        list[str]: A list of filenames of the saved images, or an empty list on error.
    """
    filenames = []
    for _ in range(num_images):
        try:
            payload = {
                "contents": [{"parts": [{"text": prompt}]}],
                "generationConfig":{
                    "responseModalities":["Text","Image"],
                }
            }
            params = {"key": GOOGLE_API_KEY}
            
            print(f"Request Payload: {payload}")
            print(f"Request Params: {params}")
            response = requests.post(API_ENDPOINT, json=payload, params=params)
            print(f"Response Status Code: {response.status_code}")
            response.raise_for_status()
            
            response_json = response.json()
            
            if "error" in response_json:
                error_message = response_json["error"].get("message", "Unknown error from Gemini API")
                print(f"Gemini API Error: {error_message}")
                continue

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
                        image_data = part["inlineData"]["data"]
                        filename = f"image_{uuid.uuid4().hex}.png"
                        filepath = os.path.join(OUTPUT_FOLDER, filename)
                        try:
                            with open(filepath, "wb") as f:
                                f.write(base64.b64decode(image_data))
                            filenames.append(filename)
                            break
                        except Exception as e:
                            print(f"Error saving image: {e}")
                    else:
                        print("Error: Image data not found in Gemini API response.")
                        print(f"Full response: {response_json}")

        except requests.exceptions.RequestException as e:
            print(f"Error making request to Gemini API: {e}")
            print(f"Full error: {e}")
        except (KeyError, ValueError, OSError) as e:
            print(f"Error processing Gemini API response: {e}")
            print(f"Full error: {traceback.format_exc()}")
        except Exception as e:
            print(f"An unexpected error occurred: {e}")
            print(f"Full error: {traceback.format_exc()}")
    return filenames


@app.route("/", methods=["GET", "POST"])
def index():
    """
    Handles the main page of the app.
    """
    image_filenames = None
    generated_prompt_text = None # Renamed to avoid confusion with original prompt
    error = None

    if request.method == "POST":
        business_name = request.form.get("businessname", "")
        slogan = request.form.get("slogan", "")
        industry = request.form.get("industry", "")

        if slogan.strip() == "":
        	# Construct the prompt dynamically based on submitted form data
            main_prompt = f"I need a colorful traditional logo for my {industry} brand named {business_name}. Use matured and professional colors. Also make sure it is tempting and attractive to the eyes. Play with the brand name and the icon. White background. In {industry} industry logo style. Leverage 60, 30, 10 color principle. Make sure the concept of the logo icon is clear and meaningful. Remember on a white background."
        else:
        	# Construct the prompt dynamically based on submitted form data
            main_prompt = f"I need a colorful traditional logo for my {industry} brand named {business_name}. Use matured and professional colors. Also make sure it is tempting and attractive to the eyes. Play with the brand name and the icon. White background. In {industry} industry logo style. Leverage 60, 30, 10 color principle. Make sure the concept of the logo icon is clear and meaningful. Remember on a white background. My business slogan is {slogan}"
        
        
        # This will be displayed as "Generated Images for prompt: ..."
        generated_prompt_text = f"{business_name}"

        if not business_name or not industry:
            error = "Business name and Industry are required fields."
        else:
            try:
                image_filenames = generate_image_with_gemini(main_prompt)
                if not image_filenames:
                    error = "Failed to generate images. Please try again."
            except Exception as e:
                error = f"An unexpected error occurred during generation: {e}"
        
        # Always render the template with the current request.form data
        # so the fields can be pre-filled.
        return render_template("index.html", 
                               image_filenames=image_filenames, 
                               prompt=generated_prompt_text, # Use the new variable for display
                               error=error,
                               request=request) # Pass the request object

    # For GET requests (initial page load)
    return render_template("index.html", request=request)


@app.route('/generated_images/<filename>')
def serve_image(filename):
    """
    Serves the generated image files from the specified output folder.
    """
    return send_from_directory(OUTPUT_FOLDER, filename)


if __name__ == "__main__":
    app.run(debug=True)