import requests
from datetime import date, timedelta, datetime

today = date.today()
yesterday = today - timedelta(days=10)
country =  "germany"
endpoint = f"https://api.covid19api.com/country/{country}/status/confirmed"
params = {"from": str(yesterday), "to": str(today)}
print(params)
endpoint_via_browser = f"https://api.covid19api.com/country/germany/status/confirmed?from=2022-12-06&to=2022-12-22"

response = requests.get(endpoint, params=params).json()
total_confirmed = 0
for day in response:
    date_python = datetime.fromisoformat(day.get("Date", 0)[:-1] + '+00:00')
    print(date_python.strftime('%Y-%m-%d'), f'{day.get("Cases", 0):_.0f}')
    cases = day.get("Cases", 0)
    total_confirmed += cases

print(f"Total Confirmed Covid-19 cases in {country}: {total_confirmed:_.0f}")

# result is : [{"Country":"Germany","CountryCode":"DE","Province":"","City":"","CityCode":"","Lat":"51.17","Lon":"10.45","Cases":36649979,"Status":"confirmed","Date":"2022-12-06T00:00:00Z"},{"Country":"Germany","CountryCode":"DE","Province":"","City":"","CityCode":"","Lat":"51.17","Lon":"10.45","Cases":36690235,"Status":"confirmed","Date":"2022-12-07T00:00:00Z"},{"Country":"Germany","CountryCode":"DE","Province":"","City":"","CityCode":"","Lat":"51.17","Lon":"10.45","Cases":36726061,"Status":"confirmed","Date":"2022-12-08T00:00:00Z"},{"Country":"Germany","CountryCode":"DE","Province":"","City":"","CityCode":"","Lat":"51.17","Lon":"10.45","Cases":36755666,"Status":"confirmed","Date":"2022-12-09T00:00:00Z"},{"Country":"Germany","CountryCode":"DE","Province":"","City":"","CityCode":"","Lat":"51.17","Lon":"10.45","Cases":36755666,"Status":"confirmed","Date":"2022-12-10T00:00:00Z"},{"Country":"Germany","CountryCode":"DE","Province":"","City":"","CityCode":"","Lat":"51.17","Lon":"10.45","Cases":36755666,"Status":"confirmed","Date":"2022-12-11T00:00:00Z"},{"Country":"Germany","CountryCode":"DE","Province":"","City":"","CityCode":"","Lat":"51.17","Lon":"10.45","Cases":36812671,"Status":"confirmed","Date":"2022-12-12T00:00:00Z"},{"Country":"Germany","CountryCode":"DE","Province":"","City":"","CityCode":"","Lat":"51.17","Lon":"10.45","Cases":36859058,"Status":"confirmed","Date":"2022-12-13T00:00:00Z"},{"Country":"Germany","CountryCode":"DE","Province":"","City":"","CityCode":"","Lat":"51.17","Lon":"10.45","Cases":36905873,"Status":"confirmed","Date":"2022-12-14T00:00:00Z"},{"Country":"Germany","CountryCode":"DE","Province":"","City":"","CityCode":"","Lat":"51.17","Lon":"10.45","Cases":36946574,"Status":"confirmed","Date":"2022-12-15T00:00:00Z"},{"Country":"Germany","CountryCode":"DE","Province":"","City":"","CityCode":"","Lat":"51.17","Lon":"10.45","Cases":36980882,"Status":"confirmed","Date":"2022-12-16T00:00:00Z"},{"Country":"Germany","CountryCode":"DE","Province":"","City":"","CityCode":"","Lat":"51.17","Lon":"10.45","Cases":36980882,"Status":"confirmed","Date":"2022-12-17T00:00:00Z"},{"Country":"Germany","CountryCode":"DE","Province":"","City":"","CityCode":"","Lat":"51.17","Lon":"10.45","Cases":36980883,"Status":"confirmed","Date":"2022-12-18T00:00:00Z"},{"Country":"Germany","CountryCode":"DE","Province":"","City":"","CityCode":"","Lat":"51.17","Lon":"10.45","Cases":37035898,"Status":"confirmed","Date":"2022-12-19T00:00:00Z"},{"Country":"Germany","CountryCode":"DE","Province":"","City":"","CityCode":"","Lat":"51.17","Lon":"10.45","Cases":37088426,"Status":"confirmed","Date":"2022-12-20T00:00:00Z"},{"Country":"Germany","CountryCode":"DE","Province":"","City":"","CityCode":"","Lat":"51.17","Lon":"10.45","Cases":37136414,"Status":"confirmed","Date":"2022-12-21T00:00:00Z"},{"Country":"Germany","CountryCode":"DE","Province":"","City":"","CityCode":"","Lat":"51.17","Lon":"10.45","Cases":37177845,"Status":"confirmed","Date":"2022-12-22T00:00:00Z"}]
