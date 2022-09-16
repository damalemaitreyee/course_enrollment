from flask import Flask, render_template, request
import os
import json
#import mysql.connector
import redis
import pyodbc
from datetime import datetime


db = None
counter = 1
account_name = "maitreyeestore"
account_key = "o2LHXv2HLxW4zRnQvIBrwo8gnRyeEc7c+Wke28bSgVZAYiL1H//9WRB2rr0l/9lL0H+GE2EIm7fO+AStNBUcWg=="
container_name = "maitreyeecontainer"
connect_str = 'DefaultEndpointsProtocol=https;AccountName=maitreyeestore;AccountKey=o2LHXv2HLxW4zRnQvIBrwo8gnRyeEc7c+Wke28bSgVZAYiL1H//9WRB2rr0l/9lL0H+GE2EIm7fO+AStNBUcWg==;EndpointSuffix=core.windows.net'

def get_sql_connection():
    server = 'maitreyeedb.database.windows.net'
    database = 'image_metadata'
    username = 'maitreyee'
    password = 'Default@123'
    cnxn = pyodbc.connect('DRIVER={ODBC Driver 17 for SQL Server};SERVER='+server+';DATABASE='+database+';UID='+username+';PWD='+password)
    return cnxn


def close_sql_connection(connection):
    connection.close()



def add_enrollment(student_id, course_num, section_num):

    # Find max enrollments for that class
    q1 = "SELECT max FROM classes where course = " + str(course_num) + " and section = " + str(section_num)
    max_count = search_query(q1)[0]['max']

    # Find current number of students in that class 
    q2 = "SELECT COUNT(*) AS count FROM enrollments WHERE course_num = " + str(course_num) + " and section_num = " + str(section_num)
    cur_count = search_query(q2)[0]['count']

    print(cur_count)
    print(max_count)
    # Add to enrollmentss
    if(int(max_count) > int(cur_count)):
        q3 = "INSERT INTO enrollments (course_num, section_num, student_id) VALUES ("+ str(course_num)+ ","+ str(section_num)+","+str(student_id)+")"
        print(q3)
        #val = (course_num, section_num, student_id)
        mydb = get_sql_connection()
        mycursor = mydb.cursor()
        mycursor.execute(q3)
        mydb.commit()
        mydb.close()
        return True
    else:
        return False

def execute_query(query):
    mydb = get_sql_connection()
    mycursor = mydb.cursor()
    mycursor.execute(query)
    mydb.commit()
    mydb.close()
    return mycursor.fetchall()

def search_query(query):
    mydb = get_sql_connection()
    mycursor = mydb.cursor()
    mycursor.execute(query)
    row_headers=[x[0] for x in mycursor.description] #this will extract row headers
    rv = mycursor.fetchall()
    json_data=[]
    for result in rv:
        json_data.append(dict(zip(row_headers,result)))
    return json_data

application = Flask(__name__)

def view_index():
    return render_template("index.html")

def get_student_view():
    fname = request.args.get("fname")
    lname = request.args.get("lname")
    return stud_view(fname, lname)
def get_admin_view():
    sid = request.args.get("id")
    #lname = request.args.get("lname")
    return adminenrollmentView(sid)

def stud_view(fname, lname):
    tables = []
    
    myDetails = search_query("SELECT * FROM students WHERE LOWER(Fname) LIKE '" + fname + "' AND LOWER(Lname) LIKE '" + lname + "'")
    print(myDetails)
    if len(myDetails) > 0:
        tables.append({
            "records": myDetails,
            "title": "Student Details"
        })
    else:
        return render_template('index.html', msg="Not a valid student") 

    myEnrollments = search_query("SELECT * FROM classes as c "+
                    "LEFT OUTER JOIN enrollments as e ON c.course = e.course_num AND c.section = e.section_num "+
                    "LEFT OUTER JOIN students as s ON s.id = e.student_id "+
                    "WHERE LOWER(s.Fname) LIKE '" + fname + "' AND LOWER(s.Lname) LIKE '" + lname + "'")
    if len(myEnrollments) > 0:
        tables.append({
            "records": myEnrollments,
            "title": "Student Enrollments"
        })
    
    if len(myEnrollments) < 3:

        addCourses = {
            "records": search_query("SELECT * FROM classes"),
            "title": "Add Enrollments",
            "student_id": myDetails[0]['id']
        }
    else:
        addCourses = None

    return render_template('index.html', tables = tables, addCourse = addCourses)
    
def get_enrollmentView():
    student_id = request.args.get("student_id")
    print(student_id)
    course_num = request.args.get("course")
    section_num = request.args.get("section")
    flag = add_enrollment(student_id, course_num, section_num)
    if flag:
        return render_template('index.html', msg = "Course Added")
    else:
        return render_template('index.html', msg="Class already full")

def adminView():
    tables = []
    print("SELECT SELECT COUNT(*) as count, section_num, course_num From enrollments GROUP BY course_num, section_num")
    count_enrollments = search_query("SELECT COUNT(*) as count, section_num, course_num From enrollments GROUP BY course_num, section_num")
    if(len(count_enrollments)) > 0:
        tables.append({
            "records": count_enrollments,
            "title": "Count Enrollments"
        })
    enrollments = search_query("SELECT * FROM enrollments as e "+
                    "LEFT OUTER JOIN classes as c ON c.course = e.course_num AND c.section = e.section_num "+
                    "LEFT OUTER JOIN students as s ON s.id = e.student_id ")
    if(len(enrollments)) > 0:
        tables.append({
            "records": enrollments,
            "title": "All Enrollments"
        })
    return render_template('admin.html', tables = tables)

def adminenrollmentView(sid):
    tables = []
    
    enrollments = search_query("SELECT * FROM enrollments as e "+
                    "LEFT OUTER JOIN students as s ON s.id = e.student_id where e.student_id = "+ str(sid))
    if(len(enrollments)) > 0:
        tables.append({
            "records": enrollments,
            "title": "All Enrollments"
        })
    return render_template('admin.html', tables = tables)

def scaleView():
    global counter
    counter = counter + 1
    return render_template('scale.html', time = datetime.now(), count = counter-1)

# add a rule for the index page.
application.add_url_rule('/', 'index', view_index)

application.add_url_rule('/api/student', 'studentView', get_student_view, methods=["GET"])
application.add_url_rule('/api/addEnrollment', 'enrollmentView', get_enrollmentView, methods=["GET"])

application.add_url_rule('/admin', 'adminView', adminView)
application.add_url_rule('/adminenrollment', 'adminenrollmentView', get_admin_view, methods=["GET"])

application.add_url_rule('/scale', 'scaleView', scaleView)

# run the app.
if __name__ == "__main__":
    application.debug = True
    application.run()


