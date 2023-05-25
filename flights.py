#
# Indiana Wing Commemorative Air Force
#     Warbird Rides Management System
#         Server side
#         Manage Flight Information
#
#   Jim Olivi 2022
#
from datetime import datetime
from globals import globals as gl, NoFlights, signals as s, format_time, scrub_phone
from flask import flash
from aircraft_model import getOneAirplane
from bson.json_util import dumps

class Flights:
    def __init__(self, data_base):
        self.db = data_base

# See how many seats are left on a flight.
# Returned is an array: [Prime Seats Sold, Passenger Seats Sold]
    def __seatsLeft(self, flight):
        primeSeatsSold = 0
        passengerSeatsSold = 0
        if gl.DB_TRANSACTIONS in flight:
            for transaction in flight[gl.DB_TRANSACTIONS]:
                if gl.DB_PRIME_SEATS in transaction:
                    primeSeatsSold += len(transaction[gl.DB_PRIME_SEATS])
                if gl.DB_PASSENGER_SEATS in transaction:
                    passengerSeatsSold += len(transaction[gl.DB_PASSENGER_SEATS])
        primeSeatsLeft = flight[gl.DB_NUM_PRIME_SEATS] - primeSeatsSold
        passengerSeatsLeft = flight[gl.DB_NUM_PASS_SEATS] - passengerSeatsSold
        return primeSeatsLeft, passengerSeatsLeft

# Get all flights.
    def get_flights(self):
        flights = self.db.get_flights(gl.DB_AIRPORT_NAME,
                                    gl.DB_FLIGHT_TIME,
                                    gl.DB_N_NUMBER)
        flight_list = []
        if flights is not None and flights[1] == "":
            for flight in flights[0]:
                airplane = self.db.get_one_airplane(flight[gl.DB_N_NUMBER], gl.DB_AIRCRAFT_NAME)
                if airplane is None:
                    flight[gl.DB_AIRCRAFT_NAME] = flight[gl.DB_N_NUMBER] + " " + gl.MSG_AIRPLANE_NOT_ON_DATABASE
                else:
                    if "_id" in airplane:
                        airplane.pop("_id")
                    flight[gl.DB_AIRCRAFT_NAME] = airplane[gl.DB_AIRCRAFT_NAME]

                # str_flight_date = flight[gl.DB_FLIGHT_TIME].strftime("%m/%d/%Y")
                flight[gl.DB_FLIGHT_TIME] = format_time(flight[gl.DB_FLIGHT_TIME])
                flight_list.append(flight)

        return flight_list

# Returns a python dictionary, not JSON-able
    def getfutureflights(self, **req):

        flight_list = self.db.get_flights(gl.DB_AIRPORT_NAME,
                                         gl.DB_AIRPORT_CITY,
                                         gl.DB_AIRPORT_CODE,
                                         gl.DB_FLIGHT_TIME,
                                          gl.DB_NUM_PRIME_SEATS,
                                          gl.DB_NUM_PASS_SEATS,
                                          gl.DB_TRANSACTIONS,
                                         startdate=req['startdate'])

        # Keep only one per day, do not return other flights.
        # Format the datetime to date only
        if flight_list[0] is None:
            flash(flight_list[1], 'error')
            raise NoFlights

        lastAirport = ""
        dayFlights = []
        for flight in flight_list[0]:
            seats = self.__seatsLeft(flight)
            if seats[0] > 0 or seats[1] > 0:
                if lastAirport != flight[gl.DB_AIRPORT_CODE]:   # New airport, reset date.
                    lastDate = ""    # Initialize date to pick first entry
                    lastAirport = flight[gl.DB_AIRPORT_CODE]

                date_time = format_time(flight[gl.DB_FLIGHT_TIME])
                date_parts = date_time.split(",")
                flight[gl.DB_FLIGHT_TIME] = date_parts[0]
                date = date_parts[0]

                if lastDate != date:
                    lastDate = date
                    dayFlights.append(flight)

        return dayFlights

# Get all flights for one day
    def get_day_flights(self, **req):
        flight_list = self.db.get_flights(gl.DB_N_NUMBER,
                                         gl.DB_AIRPORT_NAME,
                                         gl.DB_AIRPORT_CITY,
                                         gl.DB_AIRPORT_CODE,
                                         gl.DB_FLIGHT_TIME,
                                         gl.DB_FLIGHT_ID,
                                                   startdate=req['startdate'],
                                                   enddate=req['enddate'],
                                                   airportcode=req['airportcode'])


# Get Aircraft Name
        if flight_list[1] != "":
            print(gl.MSG_DATABASE_ERROR)
            print(flight_list[1])
            raise ValueError

        flight_list = flight_list[0]
        for flight in flight_list:
            airplane = self.db.get_one_airplane(flight[gl.DB_N_NUMBER], gl.DB_AIRCRAFT_NAME)
            airplane_name = airplane[gl.DB_AIRCRAFT_NAME]
            # Put the airplane name in the field to be displayed.
            flight[gl.DB_N_NUMBER] = flight[gl.DB_N_NUMBER] + ': ' + airplane_name

        # print(flight_list)
        flight_list_json = dumps(flight_list)
        return flight_list_json

# Get one flight by primary key
    def get_one_flight(self, primarykey):

# Might have to format some fields for display
        flight = self.db.get_one_flight(primarykey)
        if flight is None:
            return flight

        flight[gl.DB_FLIGHT_TIME] = str(flight[gl.DB_FLIGHT_TIME])
        if gl.DB_END_FLIGHT_TIME in flight:
            flight[gl.DB_END_FLIGHT_TIME] = flight[gl.DB_END_FLIGHT_TIME]
        else:
            flight[gl.DB_END_FLIGHT_TIME] = ""
        if flight[gl.DB_PILOT] != "Select":
            name = self.db.get_person(flight[gl.DB_PILOT], {gl.DB_FIRST_NAME, gl.DB_LAST_NAME})
            if name is not None:
                flight["pilot_name"] = f"{name[gl.DB_FIRST_NAME]} {name[gl.DB_LAST_NAME]}"
        if flight[gl.DB_CO_PILOT] != "Select":
            name = self.db.get_person(flight[gl.DB_CO_PILOT], {gl.DB_FIRST_NAME, gl.DB_LAST_NAME})
            if name is not None:
                flight["co_pilot_name"] = f"{name[gl.DB_FIRST_NAME]} {name[gl.DB_LAST_NAME]}"
        if flight[gl.DB_CREWCHIEF] != "Select":
            name = self.db.get_person(flight[gl.DB_CREWCHIEF], {gl.DB_FIRST_NAME, gl.DB_LAST_NAME})
            if name is not None:
                flight["crew_chief_name"] = f"{name[gl.DB_FIRST_NAME]} {name[gl.DB_LAST_NAME]}"
        if flight[gl.DB_LOAD_MASTER] != "Select":
            name = self.db.get_person(flight[gl.DB_LOAD_MASTER], {gl.DB_FIRST_NAME, gl.DB_LAST_NAME})
            if name is not None:
                flight["loadmaster_name"] = f"{name[gl.DB_FIRST_NAME]} {name[gl.DB_LAST_NAME]}"
        return flight

    def CreateFlight(self, form, n_number):
        # airport_code = form.airport_code.data

        flight = {
            gl.DB_N_NUMBER: n_number,
            gl.DB_AIRPORT_CODE: form.airport_code.data.upper(),
            gl.DB_AIRPORT_NAME: form.airport_name.data,
            gl.DB_PRIME_PRICE: form.premium_price.data,
            gl.DB_NUM_PRIME_SEATS: form.number_prime_seats.data,
            gl.DB_PASSENGER_PRICE: form.passenger_price.data,
            gl.DB_NUM_PASS_SEATS: form.number_pass_seats.data,
            gl.DB_FLIGHT_TIME: form.flight_time.data,
            gl.DB_END_FLIGHT_TIME: form.end_flight_time.data,
            gl.DB_PILOT: form.pilots.data,
            gl.DB_CO_PILOT: form.co_pilots.data,
            gl.DB_CREWCHIEF: form.crew_chiefs.data,
            gl.DB_LOAD_MASTER: form.loadmasters.data,
            gl.DB_AIRPORT_CITY: form.airport_city.data}
        print(flight)
        res = self.db.saveFlight(flight)
        return res

# Save passenger info for a flight.
    def passenger(self, passenger_contact_form):

        flight_id = passenger_contact_form.flight_id.data

        flight = self.db.get_one_flight(flight_id)
        if flight is None:
            flash(f'Failed to read flight record for {flight_id}', 'error')
            return s.database_op_failure

    # Create the new transaction record
        trans_record = {gl.DB_FIRST_NAME: passenger_contact_form.first_name.data,
                        gl.DB_LAST_NAME: passenger_contact_form.last_name.data,
                        gl.DB_ADDRESS: passenger_contact_form.pass_addr.data,
                        gl.DB_CITY: passenger_contact_form.pass_city.data,
                        gl.DB_STATE: passenger_contact_form.state_province.data,
                        gl.DB_POSTAL_CODE: passenger_contact_form.pass_postal.data,
                        gl.DB_EMAIL: passenger_contact_form.pass_email.data,
                        gl.DB_PHONE_NUMBER: scrub_phone(passenger_contact_form.pass_phone.data),
                        gl.DB_OK_TO_TEXT: passenger_contact_form.OKtoText.data,
                        gl.DB_TOTAL_PRICE: passenger_contact_form.total_price.data
                        }

        primeSeatsSold = 0
        passengerSeatsSold = 0
        prime_seats = []
        passenger_seats = []

        for passenger in passenger_contact_form.prime_name.raw_data:
            if passenger != '':
                prime_seats.append(passenger)
                primeSeatsSold += 1
                flash(f'{passenger}, {gl.MSG_BOOKED}', 'message')

        for passenger in passenger_contact_form.passenger_name.raw_data:
            if passenger != '':
                passenger_seats.append(passenger)
                passengerSeatsSold += 1

        seatsLeft = self.__seatsLeft(flight)
        if gl.DB_TRANSACTIONS in flight:
            for transaction in flight[gl.DB_TRANSACTIONS]:
                if gl.DB_PRIME_SEATS in transaction:
                    primeSeatsSold += len(transaction[gl.DB_PRIME_SEATS])
                if gl.DB_PASSENGER_SEATS in transaction:
                    passengerSeatsSold += len(transaction[gl.DB_PASSENGER_SEATS])

        seats = seatsLeft[0] + seatsLeft[1]
        if seats == 0:
            flash(gl.MSG_NO_SEATS_LEFT, 'message')
            return s.failure

        for passenger in passenger_contact_form.prime_name.raw_data:
            if passenger != '':
                flash(f'{passenger}, {gl.MSG_BOOKED}', 'message')
        for passenger in passenger_contact_form.passenger_name.raw_data:
            if passenger != '':
                flash(f'{passenger}, {gl.MSG_BOOKED}', 'message')

        if len(passenger_seats) > 0:
            trans_record[gl.DB_PASSENGER_SEATS] = passenger_seats
        if len(prime_seats) > 0:
            trans_record[gl.DB_PRIME_SEATS] = prime_seats

        transaction = {gl.DB_TRANSACTIONS: trans_record}
        res = self.db.updateFlightArray(flight_id, transaction)

        return res

    def getFlightInfo(self, flight, pass_form, flight_key):
        plane = getOneAirplane(self.db, flight[gl.DB_N_NUMBER])
        if plane is not None:
            pass_form.prime_seat_price = flight[gl.DB_PRIME_PRICE]
            pass_form.pass_seat_price = flight[gl.DB_PASSENGER_PRICE]
            pass_form.flight_id.data = flight_key

            flightTime = flight[gl.DB_FLIGHT_TIME].split(" ")
            month = flightTime[0].split("-")[1]
            day = flightTime[0].split("-")[2]
            year = flightTime[0].split("-")[0]
            hour = int(flightTime[1].split(":")[0])
            minute = flightTime[1].split(":")[1]
            hour = hour % 12
            if hour == 0:
                hour = 12
            if hour > 12:
                ampm = "PM"
            else:
                ampm = "AM"
            strFlightTime = f'{month}/{day}/{year} {str(hour)}:{minute}{ampm}'
            pass_form.card_title.label = flight[gl.DB_AIRPORT_NAME] + ", " + strFlightTime + " " + plane[
                gl.DB_AIRCRAFT_NAME]
        else:
            pass_form.pass_available_seats = 0
            pass_form.prime_available_seats = 0
            flash(f'{flight[gl.DB_N_NUMBER]}, {gl.MSG_AIRPLANE_NOT_ON_DATABASE}', 'error')
            pass_form.card_title.label = gl.MSG_AIRPLANE_NOT_ON_DATABASE

        num_prime_seats = 0
        num_passenger_seats = 0
        primes = ()
        passengers = ()
        if gl.DB_TRANSACTIONS in flight:
            for transaction in flight[gl.DB_TRANSACTIONS]:
                if gl.DB_PRIME_SEATS in transaction:
                    num_prime_seats = num_prime_seats + len(transaction[gl.DB_PRIME_SEATS])  # Grab number of prime seats
                if gl.DB_PASSENGER_SEATS in transaction:
                    num_passenger_seats = num_passenger_seats + len(
                        transaction[gl.DB_PASSENGER_SEATS])  # Grab number of passenger seats

            # Now create the empty seats.
            num_prime_seats = flight[gl.DB_NUM_PRIME_SEATS] - num_prime_seats
            for i in range(num_prime_seats):
                primes = primes + ("",)

            num_passenger_seats = flight[gl.DB_NUM_PASS_SEATS] - num_passenger_seats
            for i in range(num_passenger_seats):
                passengers = passengers + ("",)
        else:
            # No transactions means no seats yet sold.
            for i in range(flight[gl.DB_NUM_PRIME_SEATS]):
                primes = primes + ("",)

            for i in range(flight[gl.DB_NUM_PASS_SEATS]):
                passengers = passengers + ("",)

        return passengers, primes

