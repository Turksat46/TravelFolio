import flask
from flask import Flask, request, render_template, jsonify
from fast_flights import FlightData, Passengers, Result, get_flights

app = Flask(__name__)
@app.route('/')
def hello_world():
    return 'Hello World!'

@app.route('/api/search', methods=['POST'])
def search():
    data = request.get_json()
    origin = data.get('origin')
    destination = data.get('destination')
    departure_time = data.get('departure_time')
    try:
        passengers = Passengers()
    except Exception as e:
        return jsonify({'error': str(e)}), 400

if __name__ == '__main__':
    app.run(debug=True)
