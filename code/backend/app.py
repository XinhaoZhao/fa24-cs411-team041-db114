from flask import Flask, request, jsonify
from flask_cors import CORS
from database import createEngine
from sqlalchemy import text
import uuid
from collections import defaultdict
from datetime import datetime
import random
import string

def generate_user_id():
    """generate a random string as UserID (length = 40)"""
    return ''.join(random.choices(string.ascii_letters + string.digits, k=40))

def generate_job_id():
    """generate a random string as JobID (length = 200)"""
    return ''.join(random.choices(string.ascii_letters + string.digits, k=200))

app = Flask(__name__)
CORS(app)

# Temporary data storage (will be replaced with database later)
jobs_data = [
    {"id": 1, "title": "Software Engineer", "company": "Google", "location": "Mountain View"},
    {"id": 2, "title": "Data Scientist", "company": "Amazon", "location": "Seattle"},
]

favorite_jobs = []
user_submitted_jobs = []

@app.route('/api/jobs', methods=['GET'])
def get_jobs():
    job_title = request.args.get('jobTitle', default='', type=str)
    company_name = request.args.get('companyName', default='', type=str)
    sponsored = request.args.get('sponsored', default='', type=str)

    engine = createEngine()

    query = 'select * from Job WHERE 1=1'
    if job_title:
        query += f" AND JobTitle LIKE :job_title"
    if company_name:
        query += f" AND CompanyName LIKE :company_name"
    if sponsored:
        query += f" AND Sponsored = :sponsored"
    query += ' AND ApprovalStatus = TRUE LIMIT 50'  # Add the LIMIT at the end

    with engine.connect() as connection:
        result = connection.execute(text(query),{
            "job_title": f"%{job_title}%",  # Use wildcard for partial matching
            "company_name": f"%{company_name}%",
            "sponsored": sponsored
        })
        jobs = [dict(row._mapping) for row in result]
    return jsonify(jobs)

# @app.route('/api/jobs/submit', methods=['POST'])
# def submit_job():
#     new_job = request.json
#     cname = new_job['CompanyName']
#     companyquery = f"select CompanyName from Company where CompanyName = '{cname}'"
#     new_job['JobID'] = str(uuid.uuid4())

#     columns = ', '.join(new_job.keys())  # keys will be the column names
#     values = ', '.join([f":{key}" for key in new_job.keys()])  # placeholders for SQL query
#     # Define the SQL query with placeholders
#     query = text(f"""
#         INSERT INTO Job ({columns})
#         VALUES ({values})
#     """)
#     print(query)
#     engine = createEngine()
#     with engine.connect() as connection:
#         result = connection.execute(text(companyquery))
#         if result.rowcount == 0:
#             return jsonify({"success":False,"error":'Company not found'}), 201
#         try:
#             connection.execute(query, new_job)  # Insert job data
#             connection.commit()
#             return jsonify({"success": True}), 201  # Successfully created
#         except Exception as e:
#             return jsonify({"success": False, "error": str(e)}), 500  # Internal server error

# @app.route('/api/jobs/<job_id>', methods=['DELETE'])
# def del_job(job_id):
#     try:
#         # Ensure the job_id is a valid UUID string
#         uuid_obj = uuid.UUID(job_id)  # This will raise an exception if invalid
#     except ValueError:
#         return jsonify({"error": "Invalid UUID format"}), 400
#     # Define the SQL query to delete the job by UUID
#     query = text("DELETE FROM Job WHERE JobId = :job_id")
#     # Execute the query
#     engine = createEngine()
#     with engine.connect() as connection:
#         try:
#             result = connection.execute(query, {"job_id": job_id})
#             connection.commit()
#             if result.rowcount > 0:
#                 return jsonify({"message": f"Job with ID {job_id} has been deleted."}), 200
#             else:
#                 return jsonify({"error": "Job not found"}), 404
#         except Exception as e:
#             return jsonify({"error": f"Failed to delete job: {str(e)}"}), 500

# @app.route('/api/jobs/<job_id>', methods=['PUT'])
# def update_job(job_id):
#     data = request.get_json()
#     job_id= data['JobID']
#     # Define the SQL query to update the job
#     query = text("""
#         UPDATE Job
#         SET JobTitle = :job_title,
#             CompanyName = :company_name,
#             Sponsored = :sponsored
#         WHERE JobID = :job_id
#     """)

#     # Ensure to get values from the request JSON, with fallbacks to existing values
#     job_title = data.get('jobTitle', None)
#     company_name = data.get('companyName', None)
#     sponsored = data.get('sponsored', None)
#     print(job_id)
#     # Prepare a dictionary with values to be updated
#     params = {
#         'job_title': job_title,
#         'company_name': company_name,
#         'sponsored': sponsored,
#         'job_id': job_id
#     }

#     engine = createEngine()
#     with engine.connect() as connection:
#         # Execute the update query
#         result = connection.execute(query, params)
#         connection.commit()
#         # Check if the job was found and updated
#         if result.rowcount == 0:
#             return jsonify({'message': 'Job not found'}), 404

#     return jsonify({'message': 'Job updated successfully'}), 200

@app.route('/api/job-stats', methods=['GET'])
def get_job_stats():
    try:
        engine = createEngine()
        result = {
            'salaryData': None,
            'locationData': None,
            'jobTypeData': None
        }
        
        with engine.connect() as connection:
            # Salary distribution
            try:
                salary_query = """
                    SELECT JobTitle as job_title, AVG(CAST(Salary AS DECIMAL)) as avg_salary
                    FROM Job
                    WHERE Salary IS NOT NULL 
                    AND Salary != ''
                    AND CAST(Salary AS DECIMAL) > 0
                    GROUP BY JobTitle
                    ORDER BY avg_salary DESC
                    LIMIT 10
                """
                salary_result = connection.execute(text(salary_query))
                salary_data = {
                    'labels': [],
                    'datasets': [{
                        'label': 'Average Salary',
                        'data': [],
                        'backgroundColor': 'rgba(53, 162, 235, 0.5)',
                    }]
                }
                for row in salary_result:
                    salary_data['labels'].append(row.job_title)
                    salary_data['datasets'][0]['data'].append(float(row.avg_salary))
                result['salaryData'] = salary_data
            except Exception as e:
                print(f"Error in salary query: {str(e)}")

            # Location distribution
            try:
                location_query = """
                    SELECT CompanyName as location, COUNT(*) as job_count
                    FROM Job
                    WHERE CompanyName IS NOT NULL 
                    AND CompanyName != ''
                    GROUP BY CompanyName
                    ORDER BY job_count DESC
                    LIMIT 10
                """
                location_result = connection.execute(text(location_query))
                location_data = {
                    'labels': [],
                    'datasets': [{
                        'label': 'Number of Jobs by Company',
                        'data': [],
                        'backgroundColor': 'rgba(75, 192, 192, 0.5)',
                    }]
                }
                for row in location_result:
                    location_data['labels'].append(row.location)
                    location_data['datasets'][0]['data'].append(row.job_count)
                result['locationData'] = location_data
            except Exception as e:
                print(f"Error in location query: {str(e)}")

            # Job type distribution
            try:
                jobtype_query = """
                    SELECT JobTitle as job_title, COUNT(*) as job_count
                    FROM Job
                    WHERE JobTitle IS NOT NULL 
                    AND JobTitle != ''
                    GROUP BY JobTitle
                    ORDER BY job_count DESC
                    LIMIT 10
                """
                jobtype_result = connection.execute(text(jobtype_query))
                jobtype_data = {
                    'labels': [],
                    'datasets': [{
                        'data': [],
                        'backgroundColor': [
                            'rgba(255, 99, 132, 0.5)',
                            'rgba(54, 162, 235, 0.5)',
                            'rgba(255, 206, 86, 0.5)',
                            'rgba(75, 192, 192, 0.5)',
                            'rgba(153, 102, 255, 0.5)',
                            'rgba(255, 159, 64, 0.5)',
                            'rgba(255, 99, 132, 0.5)',
                            'rgba(54, 162, 235, 0.5)',
                            'rgba(255, 206, 86, 0.5)',
                            'rgba(75, 192, 192, 0.5)',
                        ],
                    }]
                }
                for row in jobtype_result:
                    jobtype_data['labels'].append(row.job_title)
                    jobtype_data['datasets'][0]['data'].append(row.job_count)
                result['jobTypeData'] = jobtype_data
            except Exception as e:
                print(f"Error in job type query: {str(e)}")

            return jsonify(result)

    except Exception as e:
        print(f"Error in get_job_stats: {str(e)}")
        return jsonify({'error': str(e)}), 500
    

@app.route('/api/login', methods=['POST'])
def login():
    data = request.json
    username = data.get('username')
    password = data.get('password')
    isAdmin = data.get('isAdmin')

    query = text("""
        SELECT * FROM User 
        WHERE UserName = :UserName AND Password = :Password AND is_Admin = :is_Admin
    """)

    engine = createEngine()
    with engine.connect() as connection:
        result = connection.execute(query, {
            "UserName": username,
            "Password": password,
            "is_Admin": isAdmin
        }).fetchone()

    if result:
        print('\n\n current user_id: ' + result[0] + '\n\n')
        return jsonify({"success": True, "user_id": result[0]}), 200
    else:
        return jsonify({"success": False, "error": "Invalid credentials"}), 401


@app.route('/api/register', methods=['POST'])
def register_user():
    data = request.json
    username = data.get('username')
    password = data.get('password')
    first_name = data.get('firstName')
    last_name = data.get('lastName')
    age = data.get('age')
    location = data.get('location')
    phone_number = data.get('phoneNumber')
    email_address = data.get('emailAddress')

    if not all([username, password, first_name, last_name, age, location, phone_number, email_address]):
        return jsonify({"success": False, "error": "All fields are required"}), 400

    user_id = generate_user_id()

    query = text("""
        INSERT INTO User (UserName, UserID, Password, is_Admin, FirstName, LastName, Age, Location, PhoneNumber, EmailAddress)
        VALUES (:username, :user_id, :password, FALSE, :first_name, :last_name, :age, :location, :phone_number, :email_address)
    """)

    engine = createEngine()
    with engine.connect() as connection:
        connection.execute(query, {
            "username": username,
            "user_id": user_id,
            "password": password,
            "first_name": first_name,
            "last_name": last_name,
            "age": age,
            "location": location,
            "phone_number": phone_number,
            "email_address": email_address
        })
        connection.commit()

    return jsonify({"success": True, "message": "User registered successfully"}), 201



# 下面这个我随便写的，是为了提醒，处理'''当前登录'''用户的收藏
# @app.route('/api/favorites', methods=['GET'])
# def get_favorites():
#     user_id = request.args.get('user_id') # 这里是从前端返回的当前用户的用户id

#     query = text("""         
#     """)
#     return 0


@app.route('/api/admin/pending-jobs', methods=['GET'])
def get_pending_jobs():
    query = text("""
        SELECT J.JobID, J.JobTitle, J.JobSnippet, J.JobLink, J.Salary, J.CompanyName, J.Rating, UH.AdminComment
        FROM Job J
        LEFT JOIN UploadedHistory UH ON J.JobID = UH.JobID
        WHERE J.ApprovalStatus = FALSE AND (UH.AdminComment IS NULL OR UH.AdminComment != 'Reject')
    """)
    engine = createEngine()
    with engine.connect() as connection:
        result = connection.execute(query)
        jobs = [dict(row._mapping) for row in result]
    return jsonify(jobs)

@app.route('/api/admin/approve-job/<job_id>', methods=['POST'])
def approve_job(job_id):
    action = request.json.get('action')  # "accept" or "reject"

    engine = createEngine()
    with engine.connect() as connection:
        trans = connection.begin()
        try:
            if action == "accept":
                connection.execute(
                    text("""
                        UPDATE Job
                        SET ApprovalStatus = TRUE
                        WHERE JobID = :job_id
                    """),
                    {"job_id": job_id}
                )
                connection.execute(
                    text("""
                        UPDATE UploadedHistory
                        SET AdminComment = 'Accept'
                        WHERE JobID = :job_id
                    """),
                    {"job_id": job_id}
                )
            elif action == "reject":
                connection.execute(
                    text("""
                        UPDATE UploadedHistory
                        SET AdminComment = 'Reject'
                        WHERE JobID = :job_id
                    """),
                    {"job_id": job_id}
                )
            trans.commit()
        except Exception as e:
            trans.rollback()
            return jsonify({"success": False, "error": str(e)}), 500

    return jsonify({"success": True}), 200


@app.route('/api/upload-job', methods=['POST'])
def upload_job():
    data = request.json
    user_id = data.get('userID')
    job_title = data.get('jobTitle')
    job_snippet = data.get('jobSnippet')
    job_link = data.get('jobLink')
    sponsored = data.get('sponsored')
    salary = data.get('salary')
    rating = data.get('rating')
    company_name = data.get('companyName')

    if not all([user_id, job_title, job_snippet, job_link, company_name]):
        return jsonify({"success": False, "error": "Required fields are missing"}), 400

    job_id = generate_job_id()

    insert_job_query = text("""
        INSERT INTO Job (JobID, JobTitle, JobSnippet, JobLink, Sponsored, Salary, Rating, CompanyName, ApprovalStatus)
        VALUES (:job_id, :job_title, :job_snippet, :job_link, :sponsored, :salary, :rating, :company_name, FALSE)
    """)
    insert_history_query = text("""
        INSERT INTO UploadedHistory (UploadID, UserID, JobID, AdminComment)
        VALUES (:upload_id, :user_id, :job_id, '')
    """)

    engine = createEngine()
    with engine.connect() as connection:
        connection.execute(insert_job_query, {
            "job_id": job_id,
            "job_title": job_title,
            "job_snippet": job_snippet,
            "job_link": job_link,
            "sponsored": sponsored,
            "salary": salary,
            "rating": rating,
            "company_name": company_name
        })
        connection.execute(insert_history_query, {
            "upload_id": generate_user_id(), # they are the same
            "user_id": user_id,
            "job_id": job_id
        })
        connection.commit()

    return jsonify({"success": True, "message": "Job uploaded successfully"})


@app.route('/api/upload-history/<user_id>', methods=['GET'])
def get_upload_history(user_id):
    query = text("""
        SELECT J.JobID, J.JobTitle, J.JobSnippet, J.JobLink, J.Salary, J.CompanyName, UH.AdminComment
        FROM UploadedHistory UH
        JOIN Job J ON UH.JobID = J.JobID
        WHERE UH.UserID = :user_id
    """)
    engine = createEngine()
    with engine.connect() as connection:
        results = connection.execute(query, {"user_id": user_id}).fetchall()
        jobs = [{
                "JobID": row[0],
                "JobTitle": row[1],
                "JobSnippet": row[2],
                "JobLink": row[3],
                "Salary": row[4],
                "CompanyName": row[5],
                "AdminComment": row[6]
            } for row in results]
    return jsonify(jobs)

@app.route('/api/update-job', methods=['POST'])
def update_job():
    data = request.json
    print(data)
    job_id = data.get('JobID')
    job_title = data.get('jobTitle')
    job_snippet = data.get('jobSnippet')
    job_link = data.get('jobLink')
    sponsored = data.get('sponsored')
    salary = data.get('salary')
    rating = data.get('rating')
    company_name = data.get('companyName')

    if not job_id:
        return jsonify({"success": False, "error": "Job ID is required"}), 400

    query = text("""
        UPDATE Job
        SET JobTitle = :job_title,
            JobSnippet = :job_snippet,
            JobLink = :job_link,
            Sponsored = :sponsored,
            Salary = :salary,
            Rating = :rating,
            CompanyName = :company_name,
            ApprovalStatus = FALSE
        WHERE JobID = :job_id
    """)

    engine = createEngine()
    with engine.connect() as connection:
        connection.execute(query, {
            "job_id": job_id,
            "job_title": job_title,
            "job_snippet": job_snippet,
            "job_link": job_link,
            "sponsored": sponsored,
            "salary": salary,
            "rating": rating,
            "company_name": company_name
        })
        connection.commit()

    return jsonify({"success": True, "message": "Job updated successfully"})


if __name__ == '__main__':
    app.run(debug=True) 