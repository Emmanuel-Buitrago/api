from flask import Flask, jsonify, request
from flask_mysqldb import MySQL
from passlib.hash import pbkdf2_sha256
from flask_cors import CORS


# Crear la instancia de la aplicación Flask
app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": "http://localhost:8100"}})
app.secret_key = 'my_secret_key'

app.config['MYSQL_HOST'] = '127.0.0.1'
app.config['MYSQL_USER'] = 'root'
app.config['MYSQL_DB'] = 'residential'


# Crear la instancia de la base de datos
mysql  = MySQL(app)


# Definir el modelo de usuario
class User:
    def __init__(self, id, username, fromname, password, association):
        self.id = id
        self.fromname = fromname
        self.username = username
        self._password_hash = pbkdf2_sha256.hash(password,salt=bytes(self.username, 'utf-8'))
        self.association = association

    @property #getter
    def password(self):
        raise AttributeError("No se puede acceder directamente a la contraseña, use '_password_hash' y 'check_password(passw)'")

    @password.setter #setter
    def password(self, newPassword):
        self._password_hash = pbkdf2_sha256.hash(newPassword,salt=bytes(self.username, 'utf-8'))

    @staticmethod
    def compare_passwords(password1, password2):
        return pbkdf2_sha256.verify(password1, password2)

# Definir el modelo de mensaje
class Message:
    def __init__(self, id, sender, subject, recipient, readed, timestamp, message):
        self.id = id
        self.sender = sender
        self.subject = subject
        self.recipient = recipient
        self.readed = readed
        self.timestamp = timestamp
        self.message = message

#crear ruta home
@app.route('/')
def Home():
    return get_credentials()

# Crear la ruta para registrar usuarios
@app.route('/register', methods=['POST'])
def register():
    response=None
    # Obtenemos los datos del usuario
    fromname = request.form.get('fromname')
    username = request.form.get('username')
    password = request.form.get('password')
    association = request.form.get('association')
    # Crear la instancia de usuario
    user = User(None, username,fromname, password,association)
    # Crear la instancia de Cursor
    cursor = mysql.connection.cursor()
    # Crear Query

    query = f"SELECT * FROM users WHERE username = '{user.username}'"
    cursor.execute(query)
    existing_user = cursor.fetchone()

    if existing_user: 
        response = jsonify(error="El nombre de usuario ya está registrado.")
        response.status_code = 400
    else:
        query = f"INSERT INTO users (username, password, association, fromname) VALUES ('{user.username}', '{user._password_hash}', '{user.association}', '{user.fromname}')"
        # Ejecutar Query
        try :
            cursor.execute(query)
            if not check_exist_table(f"messagesassociation{user.association}"):
                cursor.execute(f"CREATE TABLE messagesassociation{user.association}  (     id INT(10) UNSIGNED AUTO_INCREMENT PRIMARY KEY ,     sender VARCHAR(50) NOT NULL,     subject VARCHAR(100) NOT NULL,     recipient VARCHAR(50) NOT NULL,     readed BOOLEAN NOT NULL,     times TIMESTAMP NOT NULL,     message VARCHAR(4000) NOT NULL    );")
            query = f"INSERT INTO associations (name, participant) VALUES ('{user.association}','{user.username}')"
            cursor.execute(query)
            response = jsonify({'message': 'Usuario registrado correctamente.'})
            response.status_code = 201
        except:
            response = jsonify(error = "Error al registrar usuario")
            response.status_code = 400
    #Crear tabla de datos del usuario
    if 200 <= response.status_code <= 299  :
        if not check_exist_table(f"messages{user.username}"):
            query = f"CREATE TABLE messages{user.username} (     id INT(10) UNSIGNED AUTO_INCREMENT PRIMARY KEY ,     sender VARCHAR(50) NOT NULL,     subject VARCHAR(100) NOT NULL,     recipient VARCHAR(50) NOT NULL,     readed BOOLEAN NOT NULL,     times TIMESTAMP NOT NULL,     message VARCHAR(4000) NOT NULL    );"
            cursor.execute(query)
    # Cerrar Cursor
    cursor.close()
    # Cerrar conexión
    mysql.connection.commit()
    # Retornar respuesta
    return response

# Crear la ruta para registrar usuarios
@app.route('/register/association', methods=['POST'])
def register_associations():
    response=None
    # Obtenemos los datos del usuario
    association = request.form.get('association')
    # Crear la instancia de Cursor
    cursor = mysql.connection.cursor()
    # Crear Query

    query = f"SELECT * FROM users WHERE username = '{association}'"
    cursor.execute(query)
    existing_user = cursor.fetchone()
    if existing_user: 
        response = jsonify(error="El nombre de asociación ya está registrado.")
        response.status_code = 400
    else:
        query = f"SELECT * FROM associations WHERE name = '{association}'"
        cursor.execute(query)
        existing_user = cursor.fetchone()
        if existing_user:
            response = jsonify(error="El nombre de asociación ya está registrado.")
            response.status_code = 400            
        else:
            response = jsonify({'message': 'Usuario registrado correctamente.'})
            response.status_code = 201

    if 200 <= response.status_code <= 299  :
        if not check_exist_table(f"messagesassociation{association}"):
            query = f"CREATE TABLE messagesassociation{association} (     id INT(10) UNSIGNED AUTO_INCREMENT PRIMARY KEY ,     sender VARCHAR(50) NOT NULL,     subject VARCHAR(100) NOT NULL,     recipient VARCHAR(50) NOT NULL,     readed BOOLEAN NOT NULL,     times TIMESTAMP NOT NULL,     message VARCHAR(4000) NOT NULL    );"
            cursor.execute(query)
    # Cerrar Cursor
    cursor.close()
    # Cerrar conexión
    mysql.connection.commit()
    # Retornar respuesta
    return response

# Crear la ruta para iniciar sesión
@app.route('/login', methods=['POST'])
def login():
    response=None
    username = request.form.get('username')
    password = request.form.get('password')

    user = User(None,username,None,password,None)

    cursor = mysql.connection.cursor()
    query = f"SELECT * FROM users WHERE username = '{user.username}';"
    cursor.execute(query)
    if user.username is None or user._password_hash is None or not cursor.fetchone():
        response=jsonify({'message': 'Nombre de usuario o contraseña incorrectas!'})
        response.status_code = 400
    else:
        query = f"SELECT * FROM users WHERE username = '{user.username}'"
        cursor.execute(query)
        data = cursor.fetchone()
        if data:
            pssw = data[2]
            if pssw ==user._password_hash:
                response = jsonify({'message': 'Ingreso correcto!',
                                    'id': data[0],
                                    'fromname': data[3],
                                    'association': data[4],
                                    })
                response.status_code = 201
            else:
                response = jsonify({'message': 'Nombre de usuario o contraseña incorrectas!'})
                response.status_code = 400
        else:
            response = jsonify({'message': 'Nombre de usuario o contraseña incorrectas!'})
            response.status_code = 400
    return response

def check_exist_table(nombre_tabla):
    cursor = mysql.connection.cursor()
    consulta = f"SHOW TABLES LIKE '{nombre_tabla}'"
    cursor.execute(consulta)
    resultado = cursor.fetchone() is not None
    cursor.close()
    return resultado


def get_association_by_user(user):
    cursor = mysql.connection.cursor()
    consulta = f"SELECT * FROM users WHERE username = '{user}'"
    cursor.execute(consulta)
    resultado = cursor.fetchone()
    return resultado[4]

# Crear la ruta para enviar mensajes
@app.route('/messages/send', methods=['POST'])
def send_message():
    response = None
    sender = request.form.get('sender')
    subject = request.form.get('subject')
    recipient = request.form.get('recipient')
    readed = False
    timestamp = request.form.get('timestamp')
    messagetext = request.form.get('message')
    cursor = mysql.connection.cursor()
    message = Message(None, sender, subject, recipient, readed, timestamp, messagetext )
    try:
        if check_exist_table(f'messagesassociation{message.recipient}'):
            query = f"INSERT INTO messagesassociation{message.recipient} (sender, subject, recipient, readed, times, message) VALUES ('{message.sender}', '{message.subject}', '{message.recipient}', '{message.readed}', '{message.timestamp}', '{message.message}')"
            cursor.execute(query)
            cursor.execute(f"SELECT * FROM association WHERE name = {message.recipient}")
            association = cursor.fetchall()
            for associate in association:
                participant = associate[1] 
                cursor.execute(f"INSERT INTO message{participant}  (sender, subject, recipient, readed, times, message) VALUES ('{message.recipient}', '{message.subject}', '{participant}', '{message.readed}', '{message.timestamp}', '{message.message}')")
        elif not check_exist_table(f'messages{message.recipient}'):
            query = f"CREATE TABLE messages{message.recipient} (     id INT(10) UNSIGNED AUTO_INCREMENT PRIMARY KEY ,     sender VARCHAR(50) NOT NULL,     subject VARCHAR(100) NOT NULL,     recipient VARCHAR(50) NOT NULL,     readed BOOLEAN NOT NULL,     times TIMESTAMP NOT NULL,     message VARCHAR(4000) NOT NULL    );"
            cursor.execute(query)
        if not check_exist_table(f'messages{message.sender}'):
            query = f"CREATE TABLE messages{message.sender} (     id INT(10) UNSIGNED AUTO_INCREMENT PRIMARY KEY ,     sender VARCHAR(50) NOT NULL,     subject VARCHAR(100) NOT NULL,     recipient VARCHAR(50) NOT NULL,     readed BOOLEAN NOT NULL,     times TIMESTAMP NOT NULL,     message VARCHAR(4000) NOT NULL    );"
            cursor.execute(query)
        if not check_exist_table(f'messagesassociation{message.recipient}'):
            cursor.execute(f"INSERT INTO messages{message.recipient} (sender, subject, recipient, readed, times, message) VALUES ('{message.sender}', '{message.subject}', '{message.recipient}', '{message.readed}', '{message.timestamp}', '{message.message}')")
        cursor.execute(f"INSERT INTO messages{message.sender} (sender, subject, recipient, readed, times, message) VALUES ('{message.sender}', '{message.subject}', '{message.recipient}', '{message.readed}', '{message.timestamp}',' {message.message}')")
        response = jsonify({'message': 'Mensaje enviado correctamente.'})
        response.status_code = 201
    except:
        response = jsonify(error = "Error al enviar mensaje")
        response.status_code = 400
    cursor.close()
    mysql.connection.commit()
    return response

# Crear la ruta para recibir mensajes
@app.route('/messages/<user>', methods=['GET'])
def get_messages(user):
    
    response=None
    cur = mysql.connection.cursor()
    query = f"SELECT * FROM messages{user} "
    cur.execute(query)
    data1 = cur.fetchall()

    data_list={}
    for row in data1:
        sender = row[1]
        recipient = row[3]
        key = ""
        if user == sender:
            key = f"{recipient}"
        else: key = f"{sender}"
          # Etiqueta de la pareja sender-recipient

        if key in data_list:
            data_list[key].append(row)
        else:
            data_list[key] = [row]

    association = get_association_by_user(user)    
    query = f"SELECT * FROM messagesassociation{association} WHERE sender = '{user}' OR recipient = '{user}';  "
    cur.execute(query)
    data2 = cur.fetchall()

    key = f"{association}"  # Etiqueta para las filas donde el usuario es remitente o destinatario
    
    data_list[key] = data2

    cur.close()

    response = jsonify(data=data_list)
    response.status_code = 200

    return response 

@app.route('/credentials', methods=['GET'])
def get_credentials():
    response=None
    cur = mysql.connection.cursor()
    query = f"SELECT * FROM users "
    cur.execute(query)
    data = cur.fetchall()

    output = []

    for row in data:
        user_id = row[0]
        user_username = row[1]
        user_password = row[2]
        user_fromname = row[3]
        user_association = row[4]


        user_data = {
            'id': user_id,
            'username': user_username,
            'password': user_password,
            'fromname': user_fromname,
            'association': user_association
        }

        output.append(user_data)
    
    cur.close()

    response = jsonify(output=output)
    response.status_code = 200

    return response

if __name__ == '__main__':
    app.run(debug=True)