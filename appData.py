import os
import re

from flask import Flask, request, render_template

from flask import Flask, request, render_template
from werkzeug.utils import secure_filename
from flask import Flask , render_template , request 

import requests
import urllib.parse

app = Flask(__name__)


@app.route("/", methods=["GET", "POST"]) 
def runhome():
    return render_template("index.html") 

@app.route('/generic', methods=["GET", "POST"])
def generic():
    return render_template("generic.html")

@app.route('/furniture', methods=["GET", "POST"])
def furniture():
    return render_template("furniture.html")

@app.route('/electronics', methods=["GET", "POST"])
def electronics():
    return render_template("electronics.html")

@app.route('/handcrafts', methods=["GET", "POST"])
def handcrafts():
    return render_template("handcrafts.html")

@app.route('/generic_filtered', methods=["GET", "POST"])
def generic_filtered():
    return render_template("generic_filtered.html")


################################ Google Cloud Vision - Keyword Phrase Generation ##########################################

import os
from google.cloud import vision
from math import sqrt

# Set Google Cloud credentials
os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = "sunny-furnace-450323-j7-fb55f0c1398a.json"

# Define basic color names with approximate RGB values
COLOR_NAMES = {
    "Black": (0, 0, 0),
    "White": (255, 255, 255),
    "Red": (255, 0, 0),
    "Lime": (0, 255, 0),
    "Blue": (0, 0, 255),
    "Yellow": (255, 255, 0),
    "Cyan": (0, 255, 255),
    "Magenta": (255, 0, 255),
    "Silver": (192, 192, 192),
    "Gray": (128, 128, 128),
    "Maroon": (128, 0, 0),
    "Olive": (128, 128, 0),
    "Green": (0, 128, 0),
    "Purple": (128, 0, 128),
    "Teal": (0, 128, 128),
    "Navy": (0, 0, 128),
    "Orange": (255, 165, 0),
    "Pink": (255, 192, 203),
    "Brown": (165, 42, 42),
    "Gold": (255, 215, 0)
}

def closest_color(requested_color):
    """Find the closest human-readable color name for an RGB value."""
    min_distance = float("inf")
    closest_name = None
    for name, rgb in COLOR_NAMES.items():
        distance = sqrt((rgb[0] - requested_color[0]) ** 2 + 
                        (rgb[1] - requested_color[1]) ** 2 + 
                        (rgb[2] - requested_color[2]) ** 2)
        if distance < min_distance:
            min_distance = distance
            closest_name = name
    return closest_name

def detect_image_features(path):
    
    client = vision.ImageAnnotatorClient()

    # Load Image
    with open(path, "rb") as image_file:
        content = image_file.read()
    image = vision.Image(content=content)
    print(f"Processing Image: {path}")

    # Label Detection
    label_response = client.label_detection(image=image)
    labels = label_response.label_annotations
    label_list = [(label.description, label.score) for label in labels]
    print("\nDetected Labels:")
    for label in label_list:
        print(f"  - {label[0]} (Confidence: {label[1]:.2f})")

    # Object Detection
    object_response = client.object_localization(image=image)
    objects = object_response.localized_object_annotations
    object_list = [(obj.name, obj.score) for obj in objects]
    print("\nDetected Objects:")
    for obj in object_list:
        print(f"  - {obj[0]} (Confidence: {obj[1]:.2f})")

    # Logo Detection (Brand Extraction)
    logo_response = client.logo_detection(image=image)
    logos = logo_response.logo_annotations
    logo_list = [(logo.description, logo.score) for logo in logos]
    print("\nDetected Logos:")
    for logo in logo_list:
        print(f"  - {logo[0]} (Confidence: {logo[1]:.2f})")

    # OCR - Text Detection (Backup for Brand Extraction)
    text_response = client.text_detection(image=image)
    texts = text_response.text_annotations
    text_detected = texts[0].description if texts else None
    print("\nDetected Text:")
    if text_detected:
        print(f"  - Extracted Text: {text_detected}")
    else:
        print("  - No text detected.")

    # Color Detection
    image_props_response = client.image_properties(image=image)
    props = image_props_response.image_properties_annotation
    color_list = []
    
    print("\nDetected Colors:")
    for color in props.dominant_colors.colors[:3]:  # Get top 3 colors
        rgb_value = (int(color.color.red), int(color.color.green), int(color.color.blue))
        color_name = closest_color(rgb_value)  # Convert RGB to color name
        
        # Append color name and confidence score
        color_list.append((color_name, color.score))
        print(f"  - RGB: {rgb_value} → Color: {color_name} (Confidence: {color.score:.2f})")

    # Remove duplicate colors (if top 2 colors are the same, keep only one)
    dominant_colors = sorted(color_list, key=lambda x: x[1], reverse=True)[:2]  # Get top 2
    if len(dominant_colors) > 1 and dominant_colors[0][0] == dominant_colors[1][0]:
        dominant_colors = [dominant_colors[0]]  # Keep only one instance
    
    # Extract the most confident data
    detected_objects = sorted(object_list, key=lambda x: x[1], reverse=True)[:1]
    top_labels = sorted(label_list, key=lambda x: x[1], reverse=True)[:2]
    detected_brand = sorted(logo_list, key=lambda x: x[1], reverse=True)[:1]

    print("\nProcessing Keyword Sentence...")

    import nltk
    from nltk.corpus import words
    
    # Download word list if not already downloaded
    nltk.download('words')
    
    # Get a set of common English words
    common_words = set(words.words())

    # Additional custom stopwords (optional)
    custom_stopwords = {"HDMI", "DELETE", "ENTER", "END", "SUPER", "SPORT", "BICYCLE"}

    # Determine the brand name
    brand_keyword = detected_brand[0][0] if detected_brand else None

    # If no logo detected, use OCR-extracted text as backup
    if not brand_keyword and text_detected:
        words = text_detected.split()
        for word in words:
            if (word.istitle() or word.isupper()) and word not in common_words and word not in custom_stopwords:
                brand_keyword = word
                print(f"\nBrand extracted from OCR: {brand_keyword}")
                break
 
    # Constructing the keyword sentence
    color_keywords = [color[0] for color in dominant_colors]
    object_keywords = [obj[0] for obj in detected_objects]
    label_keywords = [label[0] for label in top_labels]

    description_parts = []
    if color_keywords:
        description_parts.append(" and ".join(color_keywords))
    if brand_keyword:
        description_parts.append(brand_keyword)
    if object_keywords:
        description_parts.append(object_keywords[0])
    elif label_keywords:
        description_parts.append(label_keywords[0])

    keyword_sentence = " ".join(description_parts)
    print(f"\nGenerated Keyword Sentence: {keyword_sentence}")
    return keyword_sentence

###############################--- Amazon API Prediction ----############################################################################

import requests
import urllib.parse
import json

def fetch_amazon_products(keyword):
    print("Amazon...")
    encoded_query = urllib.parse.quote(keyword)
    print(encoded_query)
    url = f"https://real-time-amazon-data.p.rapidapi.com/search?query={encoded_query}&country=US&limit=10"
    # print(url)
    headers = {
        "x-rapidapi-key": "8eb19bc2aamsh4e1ef5967a05e31p16f94bjsn6b24c8a58270",
        "x-rapidapi-host": "real-time-amazon-data.p.rapidapi.com"
    }

    try:
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        data = response.json()
        # print(data)
        products = data.get("data", {}).get("products", [])
        print(len(products))
        product_list = []
        count=0
        for product in products[:]:
            price = product.get('product_price')
            rating = product.get('product_star_rating')

            if price is not None and rating is not None and str(price).strip() != "" and str(rating).strip() != "":              
                count+=1
                product_list.append({
                    "title": product.get("product_title", "N/A"),
                    "price": f"{price}",
                    "rating": rating,
                    "url": product.get("product_url", "#"),
                    "image": product.get("product_photo", "https://via.placeholder.com/150")
                })
                if count==5:
                    break
        print(len(product_list))        
        return product_list

    except requests.exceptions.RequestException as e:
        print("❌ Request error: For Amazon", e)
        return []


################################--- Walmart API Prediction ----############################################################################

import requests
import urllib.parse  # For URL encoding

def fetch_walmart_products(keyword):
    print("Walmart...")
    encoded_keyword = urllib.parse.quote(keyword)
    print(encoded_keyword)
    url = (
        f"https://realtime-walmart-data.p.rapidapi.com/search"
        f"?keyword={encoded_keyword}&page=1&sort=price_high"
    )
    print(url)
    headers = {
        "x-rapidapi-key": "b648230cd6mshf7d65d0e50019f9p17bb88jsn3b364e652904",
        "x-rapidapi-host": "realtime-walmart-data.p.rapidapi.com"
    }

    try:
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        data = response.json()
        # print(data)
    except requests.exceptions.RequestException as e:
        print("❌ API request error: for Walmart", e)
        return []
    except ValueError:
        print("❌ Error decoding JSON response for Walmart")
        return []

    products = data.get("results", [])
    print(len(products))

    product_list = []

    if not products:
        print("❌ No products found in the API response for Walmart.")
        return product_list
    count=0
    for product in products[:]:  # Show only first 10 products
        price = product.get('price')
        rating = product.get('rating')

        # Check if both price and rating are present and not empty
        if price is not None and rating is not None and str(price).strip() != "" and str(rating).strip() != "":
            count+=1
            product_info = {
                "title": product.get("name", "N/A"),
                "price": f"{price}",
                "rating": rating,
                "url": product.get("canonicalUrl", "#"),
                "image": product.get("image", "")
            }
            product_list.append(product_info)
            if count==5:
                break
    print(len(product_list))
    return product_list


################################--- Google Shopping API Prediction ----############################################################################

import requests
import urllib.parse  # For URL encoding

def fetch_google_products(keyword, country="us", language="en", page=1, limit=5):
    print("Google Shopping...")
    encoded_keyword = urllib.parse.quote(keyword)
    print(encoded_keyword)
    url = (
        f"https://real-time-product-search.p.rapidapi.com/deals-v2"
        f"?q={encoded_keyword}&country={country}&language={language}"
        f"&page={page}&limit={limit}&sort_by=BEST_MATCH&product_condition=ANY"
    )
    print(url)
    headers = {
        "x-rapidapi-key": "fc28df0042mshe6481c6b00d0ab4p1a2351jsn56e5916c4ac7",
        "x-rapidapi-host": "real-time-product-search.p.rapidapi.com"
    }

    try:
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        data = response.json()
        # print(data)
    except requests.exceptions.RequestException as e:
        print("❌ API request error: for Google Shopping", e)
        return []
    except ValueError:
        print("❌ Error decoding JSON response for Google Shopping")
        return []

    products = data.get("data", {}).get("products", [])
    print(len(products))
    product_list = []

    if not products:
        print("❌ No products found for Google Shopping.")
        return product_list


    count=0
    for product in products[:]:

        title = product.get("product_title", "No title")
        product_url=product.get("product_page_url","N/A")
        image_url = product.get("product_photos", [None])[0]
        

        # ✅ Extract price from offers
        offer = product.get("offer", [])
        # print(offer)
        price = "Null"
        if offer:
            offer_price = offer.get("price", "")
            if isinstance(offer_price, str):
                match = re.search(r"[\d,.]+", offer_price)
                if match:
                    try:
                        price = float(match.group().replace(",", ""))
                    except:
                        pass

        # ✅ Extract rating if present
        rating = product.get("product_rating", "Null")
        
        if price!="Null" and rating!="Null":
            count+=1
            product_list.append({
                "title": title,
                "price": price,
                "rating": rating,
                "url": product_url,
                "image": image_url
            })
            if count==5:
                break
    print(len(product_list))
    return product_list

################################--- Ikea API Prediction ----############################################################################

import requests
import urllib.parse  # For URL encoding

import requests
import urllib.parse

def fetch_ikea_products(keyword, country="us", language="en"):
    print("Ikea..")
    encoded_keyword = urllib.parse.quote(keyword)
    print(encoded_keyword)
    url = (
        f"https://ikea-api.p.rapidapi.com/keywordSearch"
        f"?keyword={encoded_keyword}&countryCode={country}&languageCode={language}"
    )
    print(url)
    headers = {
        "x-rapidapi-key": "b648230cd6mshf7d65d0e50019f9p17bb88jsn3b364e652904",
        "x-rapidapi-host": "ikea-api.p.rapidapi.com"
    }

    try:
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        products = response.json()
        # print(products)
    except requests.exceptions.RequestException as e:
        print("❌ API request error: for IKEA", e)
        return []
    except ValueError:
        print("❌ Error decoding JSON response for IKEA")
        return []
    print(len(products))
    product_list = []

    if not isinstance(products, list) or len(products) == 0:
        print("❌ No products found for IKEA.")
        return product_list
    count=0
    for product in products[:]:  # Limit to top 5 results
        price_info = product.get('price', {})
        current_price = price_info.get('currentPrice')

        # Only proceed if currentPrice exists and is not empty
        if current_price is not None and str(current_price).strip() != "":
            count+=1
            product_info = {
                "title": product.get("name", "Unknown Product"),
                "type": product.get("typeName", "Unknown Type"),
                "price": f"${current_price}",
                "url": product.get("url", "#"),
                "image": product.get("image", "")
            }
            product_list.append(product_info)
            if count==5:
                break
    print(len(product_list))

    return product_list

################################--- ETSY API Prediction ----############################################################################

import requests
import urllib.parse

def fetch_etsy_products(keyword):
    print("ETSY...")
    encoded_keyword = urllib.parse.quote(keyword)
    print(encoded_keyword)
    url = f"https://etsy-api2.p.rapidapi.com/product/search?query={encoded_keyword}"

    headers = {
        "x-rapidapi-key": "37cedf8febmshbd85ad68906c31ep1aca7ajsn11f438160bb4",
        "x-rapidapi-host": "etsy-api2.p.rapidapi.com"
    }

    try:
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        data = response.json()
        # print(data)
    except requests.exceptions.RequestException as e:
        print("❌ API request error: for Etsy", e)
        return []
    except ValueError:
        print("❌ Error decoding JSON response for Etsy")
        return []

    products = data.get("response", [])
    print(len(products))

    if not isinstance(products, list) or len(products) == 0:
        print("❌ No products found for Etsy.")
        return []

    product_list = []
    count=0
    for product in products[:]:  # Limit to top 5 results
        price_info = product.get("price", {})
        sale_price = price_info.get("salePrice")

        # Only include product if salePrice exists and is not empty
        if sale_price is not None and str(sale_price).strip() != "":
            count+=1
            product_info = {
                "title": product.get("title", "Unknown Product"),
                "price": f"${sale_price}",
                "shop": product.get("shopName", "Unknown Shop"),
                "url": product.get("productUrl", "#"),
                "image": product.get("imageUrl", "")
            }
            product_list.append(product_info)
            if count==5:
                break
    print(len(product_list))
    return product_list



################################--- Best Buy API Prediction ----############################################################################

import requests
import urllib.parse

def fetch_bestbuy_products(keyword):
    print("BestBuy...")
    print(keyword)
    encoded_keyword = urllib.parse.quote(keyword)
    print(encoded_keyword)
    url = f"https://bestbuy-product-data-api.p.rapidapi.com/bestbuy/?page=1&keyword={encoded_keyword}"
    headers = {
        "x-rapidapi-key": "b648230cd6mshf7d65d0e50019f9p17bb88jsn3b364e652904",  # Replace with valid key if needed
        "x-rapidapi-host": "bestbuy-product-data-api.p.rapidapi.com"
    }
    try:
        response = requests.get(url, headers=headers, timeout=10)
        # print(response)
        response.raise_for_status()
        products = response.json()
        print(len(products))
    except requests.exceptions.RequestException as e:
        print("❌ API request error: for BestBuy", e)
        return []
    except ValueError:
        print("❌ Error decoding JSON response for BestBuy")
        return []

    if not isinstance(products, list) or len(products) == 0:
        print("❌ No products found for BestBuy.")
        return []

    product_list = []
    # print(len(products))
    count=0
    for product in products[:]:  # Limit to top 5 results
            # Extract numeric rating using regex
            rating_text = product.get("rating", "")
            rating_match = re.search(r'Rating\s+([\d.]+)', rating_text)
            numeric_rating = rating_match.group(1) if rating_match else "N/A"

            # Extract numeric price using regex
            raw_price = str(product.get("price", "N/A"))
            price_match = re.search(r'[\d,.]+', raw_price)
            numeric_price = price_match.group(0) if price_match else "N/A"
            product_info = {
                "title": product.get("title", "Unknown Product"),
                "price": f"${numeric_price}",
                "rating": numeric_rating,
                "url": product.get("product_url", "#"),
                "image": product.get("image_url", "")
            }
            # Optional: store only if price and rating exist
            if product.get("price") and numeric_rating != "N/A":
                count+=1
                product_list.append(product_info)
                if count==5:
                    break
    print(len(product_list))
    return product_list

################################--- E-Commerce Prediction ----############################################################################



@app.route('/generic_result', methods=['POST'])
def generic_result():
    if request.method == 'POST':
        try:
            # Get the uploaded image
            file = request.files['image']

            # Save the file
            file_path = 'uploads/' + secure_filename(file.filename)
            file.save(file_path)

            print(file_path)

            # Get the text input from the form
            user_input = request.form.get('text_input', '')  # Default is empty string if not provided
            print("User input text:", user_input)

            # Placeholder image-based keyword extraction (replace with actual function)
            keyword_sentence = detect_image_features(file_path)
            # keyword_sentence = 'microwave'

            # Combine image keyword and user text input
            if user_input:
                keyword_sentence = f"{keyword_sentence} {user_input.strip()}"

            print("Final keyword phrase:", keyword_sentence)

            # Fetch product data from APIs
            amazon_products  = fetch_amazon_products(keyword_sentence)
            walmart_products = fetch_walmart_products(keyword_sentence)
            google_products  = fetch_google_products(keyword_sentence)
            ikea_products    = fetch_ikea_products(keyword_sentence)
            etsy_products    = fetch_etsy_products(keyword_sentence)
            bestbuy_products = fetch_bestbuy_products(keyword_sentence)

            return render_template('generic_result.html',
                                   keyword_sentence=keyword_sentence,
                                   amazon_products=amazon_products,
                                   walmart_products=walmart_products,
                                   google_products=google_products,
                                   ikea_products=ikea_products,
                                   etsy_products=etsy_products,
                                   bestbuy_products=bestbuy_products 
                                )

        except Exception as e:
            return render_template('error.html', error_message=str(e))


@app.route('/furniture_result', methods=['POST'])
def furniture_result():
    if request.method == 'POST':
        try:
            # Get the uploaded image
            file = request.files['image']

            # Save the file
            file_path = 'uploads/' + secure_filename(file.filename)
            file.save(file_path)

            print(file_path)

            # Get the text input from the form
            user_input = request.form.get('text_input', '')  # Default is empty string if not provided
            print("User input text:", user_input)

            # Placeholder image-based keyword extraction (replace with actual function)
            keyword_sentence = detect_image_features(file_path)
            #keyword_sentence = "Hand bag"

            # Combine image keyword and user text input
            if user_input:
                keyword_sentence = f"{keyword_sentence} {user_input.strip()}"

            print("Final keyword phrase:", keyword_sentence)

            # Fetch product data from APIs
            ikea_products    = fetch_ikea_products(keyword_sentence)
            amazon_products  = fetch_amazon_products(keyword_sentence)
            walmart_products = fetch_walmart_products(keyword_sentence)
            google_products  = fetch_google_products(keyword_sentence)
            

            return render_template('furniture_result.html',
                                   keyword_sentence=keyword_sentence,
                                   ikea_products=ikea_products,
                                   amazon_products=amazon_products,
                                   walmart_products=walmart_products,
                                   google_products=google_products
                                )

        except Exception as e:
            return render_template('error.html', error_message=str(e))
        
        
@app.route('/electronics_result', methods=['POST'])
def electronics_result():
    if request.method == 'POST':
        try:
            # Get the uploaded image
            file = request.files['image']

            # Save the file
            file_path = 'uploads/' + secure_filename(file.filename)
            file.save(file_path)

            print(file_path)

            # Get the text input from the form
            user_input = request.form.get('text_input', '')  # Default is empty string if not provided
            print("User input text:", user_input)

            # Placeholder image-based keyword extraction (replace with actual function)
            keyword_sentence = detect_image_features(file_path)
            #keyword_sentence = "washing machine"

            # Combine image keyword and user text input
            if user_input:
                keyword_sentence = f"{keyword_sentence} {user_input.strip()}"

            print("Final keyword phrase:", keyword_sentence)

            # Fetch product data from APIs
            bestbuy_products    = fetch_bestbuy_products(keyword_sentence)
            amazon_products  = fetch_amazon_products(keyword_sentence)
            walmart_products = fetch_walmart_products(keyword_sentence)
            google_products  = fetch_google_products(keyword_sentence)
            

            return render_template('electronics_result.html',
                                   keyword_sentence=keyword_sentence,
                                   bestbuy_products=bestbuy_products,
                                   amazon_products=amazon_products,
                                   walmart_products=walmart_products,
                                   google_products=google_products)

        except Exception as e:
            return render_template('error.html', error_message=str(e))


@app.route('/handcrafts_result', methods=['POST'])
def handcrafts_result():
    if request.method == 'POST':
        try:
            # Get the uploaded image
            file = request.files['image']

            # Save the file
            file_path = 'uploads/' + secure_filename(file.filename)
            file.save(file_path)

            print(file_path)

            # Get the text input from the form
            user_input = request.form.get('text_input', '')  # Default is empty string if not provided
            print("User input text:", user_input)

            # Placeholder image-based keyword extraction (replace with actual function)
            keyword_sentence = detect_image_features(file_path)
            #keyword_sentence = "Hand bag"

            # Combine image keyword and user text input
            if user_input:
                keyword_sentence = f"{keyword_sentence} {user_input.strip()}"

            print("Final keyword phrase:", keyword_sentence)

            # Fetch product data from APIs
            etsy_products    = fetch_etsy_products(keyword_sentence)
            amazon_products  = fetch_amazon_products(keyword_sentence)
            walmart_products = fetch_walmart_products(keyword_sentence)
            google_products  = fetch_google_products(keyword_sentence)
            

            return render_template('handcrafts_result.html',
                                   keyword_sentence=keyword_sentence,
                                   etsy_products=etsy_products,
                                   amazon_products=amazon_products,
                                   walmart_products=walmart_products,
                                   google_products=google_products)

        except Exception as e:
            return render_template('error.html', error_message=str(e))


        
@app.route('/generic_filtered_result', methods=['POST'])
def generic_filtered_result():
    if request.method == 'POST':
        try:
            # Get the uploaded image
            file = request.files['image']

            # Save the file
            file_path = 'uploads/' + secure_filename(file.filename)
            file.save(file_path)

            print(file_path)

            # Get the text input from the form
            user_input = request.form.get('text_input', '')  # Default is empty string if not provided
            print("User input text:", user_input)

            # Placeholder image-based keyword extraction (replace with actual function)
            keyword_sentence = detect_image_features(file_path)
            #keyword_sentence = "Hand bag"

            # Combine image keyword and user text input
            if user_input:
                keyword_sentence = f"{keyword_sentence} {user_input.strip()}"

            print("Final keyword phrase:", keyword_sentence)

            # Fetch product data from APIs
            amazon_products  = fetch_amazon_products(keyword_sentence)
            walmart_products = fetch_walmart_products(keyword_sentence)
            google_products  = fetch_google_products(keyword_sentence)
            ikea_products    = fetch_ikea_products(keyword_sentence)
            etsy_products    = fetch_etsy_products(keyword_sentence)
            bestbuy_products = fetch_bestbuy_products(keyword_sentence)

            return render_template('generic_filtered_result.html',
                                   keyword_sentence=keyword_sentence,
                                   amazon_products=amazon_products,
                                   walmart_products=walmart_products,
                                   google_products=google_products,
                                   ikea_products=ikea_products,
                                   etsy_products=etsy_products,
                                   bestbuy_products=bestbuy_products)

        except Exception as e:
            return render_template('error.html', error_message=str(e))



################################################################################################



if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
