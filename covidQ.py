from __future__ import print_function
from flask import Flask, render_template, url_for, request, flash, redirect
from forms import InputData
import os
import sys
import numpy as np
from keras.models import load_model
from PIL import Image
from werkzeug.utils import secure_filename
# import serial
from keras.preprocessing import image
from keras.applications.imagenet_utils import preprocess_input
from flask_mysqldb import MySQL
import yaml
app = Flask(__name__)


# Default values
defaultResult = "NotTested"
result = "-"

SECRET_KEY = os.urandom(32)
# SECRET KEY to prevent modifying of cookies
app.config['SECRET_KEY'] = SECRET_KEY

# Configuring the db from yaml file
db = yaml.load(open('db.yaml'))
app.config['MYSQL_HOST'] = db['mysql_host']
app.config['MYSQL_USER'] = db['mysql_user']
app.config['MYSQL_PASSWORD'] = db['mysql_password']
app.config['MYSQL_DB'] = db['mysql_db']

mysql = MySQL(app)

current_folder = os.path.abspath(os.path.dirname(__file__))
model_file = os.path.join(current_folder, 'covid_normal_pneumonia_model.h5')
global model
model = load_model(model_file)

# function for image prediction, gets called in predict


def image_prediction(imagePath, model):
    img = image.load_img(imagePath, target_size=(244, 244))
    img = image.img_to_array(img)
    img = np.expand_dims(img, axis=0)

    pred = model.predict(img)
    pred_covid = round(pred[0][0]*100, 4)
    pred_normal = round(pred[0][1] * 100, 4)
    pred_pneumonia = round(pred[0][2] * 100, 4)
    if np.argmax(pred, axis=1)[0] == 0:
        return pred_covid
    elif np.argmax(pred, axis=1)[0] == 1:
        return 100-pred_normal
    else:
        return 0.81*pred_pneumonia


# Home page
@app.route("/", methods=['GET', 'POST'])
@app.route("/home", methods=['GET', 'POST'])
def home():
    cur = mysql.connection.cursor()
    noOfPatients = cur.execute("SELECT * FROM Patient")
    patientInfo = cur.fetchall()
    return render_template('home.html', title='Home', noOfPatients=noOfPatients, values=patientInfo)


# Add a patient page
@app.route("/addAPatient", methods=['GET', 'POST'])
def add():

    #oxygen = 0
    form = InputData()
    if (form.validate_on_submit() and request.method == 'POST'):
        patientDetails = request.form
        pid = patientDetails['pid']
        fname = patientDetails['fname']
        lname = patientDetails['lname']
        age = patientDetails['age']
        spo2 = patientDetails['spo2']
        respiratory = 1 if ("respiratory" in patientDetails) else 0
        circulatory = 1 if ("circulatory" in patientDetails) else 0
        diabetes = 1 if ("diabetes" in patientDetails) else 0
        dementia = 1 if ("dementia" in patientDetails) else 0
        renal = 1 if ("renal" in patientDetails) else 0
        maligNeoplasms = 1 if ("maligNeoplasms" in patientDetails) else 0
        obesity = 1 if ("obesity" in patientDetails) else 0
        alzheimer = 1 if ("alzheimer" in patientDetails) else 0

        cur = mysql.connection.cursor()
        xray_file = request.files['xray']
        saveImg(xray_file)

        probComorbidities = calcComorbidities(
            respiratory,  circulatory,  diabetes,  dementia,  renal,  maligNeoplasms,  obesity,  alzheimer)
        probAge = calcAge(int(age))
        # prediction algorithm
        susceptibility = predict(probComorbidities, float(spo2), probAge)
        print(susceptibility, file=sys.stderr)  # printing it to the console

        cur.execute("INSERT INTO Patient VALUES(%s,%s,%s,%s,%s,%s,%s)",
                    (pid, fname, lname, age, susceptibility, result, defaultResult,))
        mysql.connection.commit()
        cur.close()
        flash("Patient ID {} added to the database".format(pid), "success")
        return redirect(url_for('home'))
    # elif(request.method=='POST' and request.form['spo2Submit']=='O2'):
    # 	oxygen = oximeter() #Oximeter
    # 	return render_template('add.html',title = 'Add',form=form, oxygen = oxygen)
    return render_template('add.html', title='Add', form=form)


# About page
@app.route("/about")
def about():
    return render_template('about.html', title='About')


# spO2 page
@app.route("/checkyourspo2", methods=['GET', 'POST'])
def checkspo2():
    oxygen = 0
    if(request.method == 'POST'):
        oxygen = oximeter()  # calling the function to take data from the oximeter
        return render_template('check.html', title='spO2', oxygen=oxygen)
    return render_template('check.html', title='spO2', oxygen=oxygen)


# Edit page
@app.route("/edit/<patientId>/", methods=['GET', 'POST'])
def editPg(patientId):
    # patientId = request.args[id]
    cur = mysql.connection.cursor()
    if (request.method == 'POST'):
        patientDetails = request.form
        selections = patientDetails.getlist('stat')[0].split(' ')
        result = patientDetails.getlist('res')
        if(len(selections) == 2):
            status = selections[0]
            result = selections[1]
            cur.execute("UPDATE Patient SET status=%s, result=%s WHERE id=%s",
                        (status, result, patientId))
        else:
            status = selections[0]
            cur.execute("UPDATE Patient SET status=%s, result=%s WHERE id=%s",
                        (status, '-', patientId,))

        mysql.connection.commit()
        cur.close()
        return redirect(url_for('home'))

    return render_template('editPage.html', title='Edit')


# Results page
@app.route("/results")
def results():
    return render_template('results.html', title='results')


# Queue page
@app.route("/queue")
def queuePage():
    cur = mysql.connection.cursor()
    noOfPatients = cur.execute(
        "SELECT * FROM Patient WHERE status!=%s ORDER BY susceptibility DESC", ("Done",))
    orderOfPatients = cur.fetchall()
    print(orderOfPatients)
    return render_template('queue.html', title='Queue', noOfPatients=noOfPatients, values=orderOfPatients)


def saveImg(xrayImg):  # Function to save the xray
    xrayImg = Image.open(xrayImg)
    xrayImg.save("xray.png")


def oximeter():
    arduino = serial.Serial('COM4', 9600)
    oxygen = arduino.readline()
    decodedOxygen = str(oxygen)
    arduino.close()
    return decodedOxygen[-7:-5]


def calcComorbidities(respiratory,  circulatory,  diabetes,  dementia,  renal,  maligNeoplasms,  obesity,  alzheimer):
    # total deaths = 569114
    return 100*(0.3999*respiratory + 0.17547*circulatory + 0.1408*diabetes + 0.0909*dementia + 0.08476*renal + 0.04063 * maligNeoplasms + 0.033835 * obesity + 0.03359 * alzheimer)


def calcAge(age):
    if age >= 0 and age <= 17:
        return 0.06
    elif age >= 18 and age <= 44:
        return 3.9
    elif age >= 45 and age <= 64:
        return 22.4
    elif age >= 65 and age <= 74:
        return 24.9
    elif age >= 75:
        return 48.7


def predict(probComorbidities, spo2, probAge):
    prediction = 0
    if(spo2 >= 95):
        probSpo2 = 0
    elif (spo2 < 95 and spo2 >= 93):
        probSpo2 = 31.7
    else:
        probSpo2 = 68.3

    xray_prob = int(image_prediction(r'xray.png', model))
    prediction = 0.72*xray_prob+0.19*probAge+0.9*probSpo2
    # TODO find more accurate ratios for the final prob
    return prediction


if(__name__ == '__main__'):
    app.run(debug=True)
