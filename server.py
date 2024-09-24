import nltk
from nltk.sentiment.vader import SentimentIntensityAnalyzer
from nltk.corpus import stopwords
from urllib.parse import parse_qs, urlparse
import json
import pandas as pd
from datetime import datetime
import uuid
import os
from typing import Callable, Any
from wsgiref.simple_server import make_server
import urllib

nltk.download('vader_lexicon', quiet=True)
nltk.download('punkt', quiet=True)
nltk.download('averaged_perceptron_tagger', quiet=True)
nltk.download('stopwords', quiet=True)

adj_noun_pairs_count = {}
sia = SentimentIntensityAnalyzer()
stop_words = set(stopwords.words('english'))

reviews = pd.read_csv('data/reviews.csv').to_dict('records')

class ReviewAnalyzerServer:
    def __init__(self) -> None:
        # This method is a placeholder for future initialization logic
        pass

    def analyze_sentiment(self, review_body):
        sentiment_scores = sia.polarity_scores(review_body)
        return sentiment_scores

    def __call__(self, environ: dict[str, Any], start_response: Callable[..., Any]) -> bytes:
        """
        The environ parameter is a dictionary containing some useful
        HTTP request information such as: REQUEST_METHOD, CONTENT_LENGTH, QUERY_STRING,
        PATH_INFO, CONTENT_TYPE, etc.
        """

        permissible_locations = [
            "Albuquerque, New Mexico",
            "Carlsbad, California",
            "Chula Vista, California",
            "Colorado Springs, Colorado",
            "Denver, Colorado",
            "El Cajon, California",
            "El Paso, Texas",
            "Escondido, California",
            "Fresno, California",
            "La Mesa, California",
            "Las Vegas, Nevada",
            "Los Angeles, California",
            "Oceanside, California",
            "Phoenix, Arizona",
            "Sacramento, California",
            "Salt Lake City, Utah",
            "San Diego, California",
            "Tucson, Arizona"
        ]

        if environ["REQUEST_METHOD"] == "GET":
            # Save the original reviews for filtering
            original_reviews = reviews.copy()

            # Create the response body from the reviews and convert to a JSON byte string
            query_string = parse_qs(environ["QUERY_STRING"])
            if query_string:
                location = query_string.get("location", [""])[0]
                start_date = query_string.get("start_date", [""])[0]
                end_date = query_string.get("end_date", [""])[0]



                # Apply filters step by step to the original reviews
                if location:
                    if location in permissible_locations:
                        original_reviews = [review for review in original_reviews if review["Location"] == location]
                    else:
                        # If location is not permissible, return an empty list
                        original_reviews = []

                if start_date:
                    start_date = datetime.strptime(start_date, "%Y-%m-%d")
                    original_reviews = [review for review in original_reviews if datetime.strptime(review["Timestamp"], "%Y-%m-%d %H:%M:%S") >= start_date]

                if end_date:
                    end_date = datetime.strptime(end_date, "%Y-%m-%d")
                    original_reviews = [review for review in original_reviews if datetime.strptime(review["Timestamp"], "%Y-%m-%d %H:%M:%S") <= end_date]

            # Add sentiment to each review
            for review in original_reviews:
                review["sentiment"] = self.analyze_sentiment(review["ReviewBody"])

            response_body = json.dumps(original_reviews, indent=2).encode("utf-8")

            # Set the appropriate response headers
            start_response("200 OK", [
                ("Content-Type", "application/json"),
                ("Content-Length", str(len(response_body)))
            ])
            
            return [response_body]


        if environ["REQUEST_METHOD"] == "POST":
            try:
                # Read the request body size
                request_body_size = int(environ.get("CONTENT_LENGTH", 0))
            except (ValueError, TypeError):
                request_body_size = 0

            try:
                # Read the request body
                request_body = environ["wsgi.input"].read(request_body_size).decode('utf-8')
                # Parse the URL-encoded string
                parsed_params = urllib.parse.parse_qs(request_body)
                # Extract parameters
                location = parsed_params.get("Location", [""])[0]
                review_body = parsed_params.get("ReviewBody", [""])[0]
            except (KeyError, Exception):
                location = ""
                review_body = ""

            # Validate the parameters
            if not location or not review_body:
                start_response("400 Bad Request", [("Content-Type", "application/json")])
                error_response = {"error": "Missing Location or ReviewBody"}
                return [json.dumps(error_response).encode("utf-8")]

            if location not in permissible_locations:
                start_response("400 Bad Request", [("Content-Type", "application/json")])
                error_response = {"error": "invalid location"}
                return [json.dumps(error_response).encode("utf-8")]

            # Add the review to the reviews list
            review = {
                "ReviewId": str(uuid.uuid4()),
                "Location": location,
                "Timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "ReviewBody": review_body
            }

            # Set the appropriate response headers
            start_response("201 Created", [("Content-Type", "application/json")])

            # Return the response body as bytes
            return [json.dumps(review).encode("utf-8")]

        # Handle other request methods if necessary
        start_response("405 Method Not Allowed", [("Content-Type", "application/json")])
        error_response = {"error": "Method Not Allowed"}
        return [json.dumps(error_response).encode("utf-8")]
    
if __name__ == "__main__":
    app = ReviewAnalyzerServer()
    port = os.environ.get('PORT', 8000)
    with make_server("", port, app) as httpd:
        print(f"Listening on port {port}...")
        httpd.serve_forever()