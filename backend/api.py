from data_ingestion.mongo_handler import MongoHandler
from flask import Flask, jsonify

app = Flask(__name__)
mongo_handler = MongoHandler()


@app.route("/api/top-stocks", methods=["GET"])
def get_top_stocks():
    quotes_col = mongo_handler.get_collection("quotes")
    # Sort by percentage change descending and limit to top 10
    cursor = quotes_col.find().sort("pChange", -1).limit(10)
    top_stocks = []
    for doc in cursor:
        doc.pop("_id", None)  # Remove MongoDB internal id
        top_stocks.append(doc)
    return jsonify(top_stocks)


if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000)
