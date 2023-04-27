# from sqlalchemy import distinct
from app import app
from flask import render_template
from app.forms import CountrySearchForm, CitySearchForm, CurrencyFilterForm, CapitalSearchForm
from app import db
from app.models import Country, City, Details
import requests

API_KEY = "12fc26908dmsh28a92a7da0f3342p14538djsnae28d388b215"
API_HOST = "wft-geo-db.p.rapidapi.com"
BASE_URL = "https://wft-geo-db.p.rapidapi.com/v1/geo/"

@app.route('/')
def home():
    return render_template('home.html')

@app.route('/populate_db')
def populate_db():
    base_url = "https://wft-geo-db.p.rapidapi.com/v1/geo/"
    endpoint = base_url + 'countries/'

    headers = {
        "X-RapidAPI-Key": API_KEY,
        "X-RapidAPI-Host": API_HOST
    }

    page_number = 1
    has_more = True

    while has_more:
        querystring = {"page": page_number, "limit": 9}
        response = requests.request("GET", endpoint, headers=headers, params=querystring)

        if response.status_code != 200:
            print("Error:", response.status_code, response.content)
            return f"Error {response.status_code}: {response.content}"

        response_json = response.json()
        
        if 'links' in response_json:
            has_more = 'nextPage' in response_json['links']
        else:
            has_more = False

        for country_data in response_json['data']:
            country_name = country_data['name']
            country_code = country_data['code']
            currency_code = country_data['currencyCodes'][0] if country_data['currencyCodes'] else None

            existing_country = Country.query.filter_by(code=country_code).first()

            if existing_country is None:
                country = Country(name=country_name, code=country_code, currency_code=currency_code)
                db.session.add(country)

        db.session.commit()

        page_number += 1

    return "Database populated with countries"

@app.route('/add_country', methods=['GET', 'POST'])
def add_country():
    form = CountrySearchForm()
    countries = []
    if form.validate_on_submit():
        query = form.country_name.data
        url = f"{BASE_URL}countries?namePrefix={query}"
        headers = {
            "X-RapidAPI-Key": API_KEY,
            "X-RapidAPI-Host": API_HOST
        }
        response = requests.get(url, headers=headers)
        data = response.json()
        countries = data['data']

        for country in countries:
            db_country = Country.query.get(country['code'])
            if not db_country:
                new_country = Country(
                    code=country['code'],
                    name=country['name'],
                    currency_code=country['currencyCodes'][0]
                )
                db.session.add(new_country)
                db.session.commit()

    return render_template('add_country.html', form=form, countries=countries)

@app.route('/countries')
def countries():
    countries = Country.query.all()
    return render_template('countries.html', countries=countries)

@app.route('/search_city', methods=['GET', 'POST'])
def search_city():
    form = CitySearchForm()
    search_results = []
    if form.validate_on_submit():
        city_name = form.city_name.data
        endpoint = f"https://wft-geo-db.p.rapidapi.com/v1/geo/cities?namePrefix={city_name}&limit=10"
        headers = {
            "X-RapidAPI-Key": API_KEY,
            "X-RapidAPI-Host": API_HOST,
        }
        response = requests.get(endpoint, headers=headers)
        cities_data = response.json()["data"]

        for city_data in cities_data:
            city = City.query.get(city_data["id"])
            if city is None:
                city = City(
                    id=city_data["id"],
                    name=city_data["name"],
                    country_code=city_data["countryCode"],
                    country=city_data["country"],
                    region=city_data["region"],
                )
                db.session.add(city)
                db.session.commit()
                
        search_results = City.query.filter_by(name=city_name).all()
    return render_template('search_city.html', form=form, cities=search_results)

@app.route('/search_capital', methods=['GET', 'POST'])
def search_capital():
    form = CapitalSearchForm()
    capital = ""
    callingCode = ""
    countryName = "" 
    if form.validate_on_submit():
        query = form.ISO.data
        url = f"{BASE_URL}countries/{query}"
        headers = {
            "X-RapidAPI-Key": API_KEY,
            "X-RapidAPI-Host": API_HOST
        }
        response = requests.get(url, headers=headers)
        data = response.json()
               
        # if invalid search
        try:
            db_details = Details.query.get(data['data']['code'])
        except:
            return render_template('not_found.html')
            
        if not db_details:
            new_country = Details(
                code=data['data']['code'],
                capital=data['data']['capital'],
                calling_code=data['data']['callingCode'],
                countryName=data['data']['name'], 
            )
            db.session.add(new_country)
            db.session.commit()

        capital = data['data']['capital']
        callingCode = data['data']['callingCode']
        countryName = countryName=data['data']['name'] 
    
    return render_template('search_capital.html', form=form, callingCode=callingCode, countryName=countryName, capital=capital)

@app.route('/currency_filter', methods=['GET', 'POST'])
def currency_filter():
    form = CurrencyFilterForm()
    countries = []
    if form.validate_on_submit():
        currency_code = form.currency_code.data.upper()
        countries = Country.query.filter_by(currency_code=currency_code).all()
    return render_template('currency_filter.html', form=form, countries=countries)
