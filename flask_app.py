from flask import Flask, render_template, request, redirect, url_for, session, flash
from functools import wraps

import json
import folium

app = Flask(__name__)
app.secret_key = "tu_clave_secreta_muy_segura" # Cambia esto en produccion

# Simulación de una base de datos de usuarios
users = {
    'admin': {'password': 'adminpass', 'role': 'admin'},
    'driver1': {'password': 'driver1pass', 'role': 'driver'},
    'driver2': {'password': 'driver2pass', 'role': 'driver'},
    'driver3': {'password': 'driver3pass', 'role': 'driver'},
    'editor': {'password': 'editorpass', 'role': 'editor'}
}

# Base de datos simulada de pedidos
PEDIDOS_DB = {
    "PED001": {
        "numero": "PED001",
        "cliente": "Juan Pérez",
        "fecha": "2024-05-01",
        "direccion": "Av. Los Sauces # 345",
        "telefono": "7777 7777",
        "ciudad": "Cochabamba",
        "estado": "Pendiente",
        "articulos": [
            {"id": 1, "nombre": "Laptop Dell", "cantidad": 2, "precio": 1200.00},
            {"id": 2, "nombre": "Mouse Logitech", "cantidad": 1, "precio": 40.00},
            {"id": 3, "nombre": "Teclado Mecánico", "cantidad": 1, "precio": 80.00},
            {"id": 4, "nombre": "Monitor 24\"", "cantidad": 1, "precio": 200.00},
            {"id": 5, "nombre": "Webcam HD", "cantidad": 1, "precio": 50.00}
        ]
    },
    "PED002": {
        "numero": "PED002",
        "cliente": "Maria Garcia",
        "fecha": "2024-05-02",
        "direccion": "Av. San Martin #12",
        "telefono": "7111 2222",
        "ciudad": "Cochabamba",
        "estado": "Entregado",
        "articulos": [
            {"id": 1, "nombre": "Smartphone Samsung", "cantidad": 1, "precio": 800.00},
            {"id": 2, "nombre": "Funda Protectora", "cantidad": 2, "precio": 15.00},
            {"id": 3, "nombre": "Cargador Rápido", "cantidad": 1, "precio": 35.00},
            {"id": 4, "nombre": "Auriculares Bluetooth", "cantidad": 1, "precio": 120.00},
            {"id": 5, "nombre": "Protector de Pantalla", "cantidad": 1, "precio": 10.00}
        ]
    },
    "PED003": {
        "numero": "PED003",
        "cliente": "Carlos Lopez",
        "fecha": "2024-05-03",
        "direccion": "Av. Los Sauces # 345",
        "telefono": "7777 7777",
        "ciudad": "Cochabamba",
        "estado": "Pendiente",
        "articulos": [
            {"id": 1, "nombre": "Tablet iPad", "cantidad": 1, "precio": 600.00},
            {"id": 2, "nombre": "Apple Pencil", "cantidad": 1, "precio": 150.00},
            {"id": 3, "nombre": "Funda para Tablet", "cantidad": 1, "precio": 45.00},
            {"id": 4, "nombre": "Adaptador USB-C", "cantidad": 2, "precio": 25.00},
            {"id": 5, "nombre": "Cable Lightning", "cantidad": 1, "precio": 20.00}
        ]
    }
}

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'username' not in session:
            flash('Debes iniciar sesión para acceder a esta página.', 'error')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

@app.route('/')
def home():
    return render_template('home.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        if username in users and users[username]['password'] == password:
            # Datos correctos: Iniciar sesión
            session['username'] = username
            session['role'] = users[username]['role']
            flash('Bienvenido!', 'success')

            # Redirigir al dashboard (que mostrará los links correctos)
            # No importa si es admin, driver o editor, el dashboard es un buen lugar.
            return redirect(url_for('dashboard'))

        else:
            # Datos incorrectos
            flash('Usuario o contraseña incorrectos', 'error')
            # No es necesario un 'return' aquí, caerá al return final

    # Si el método es GET (cargar la pág. por primera vez) o si el login falló
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.pop('username', None)
    session.pop('role', None)
    flash('Has cerrado sesión.', 'info')
    return redirect(url_for('home'))

@app.route('/dashboard')
@login_required
def dashboard():
    return render_template('dashboard.html')


@app.route('/ver_mapa')
def ver_mapa():
    if 'username' not in session or session['username'] == None:
        return redirect(url_for('login'))

    # Crear el mapa centrado en Cochabamba
    m = folium.Map(location=[-17.3845, -66.1578], zoom_start=15)

    # Lista de tiendas con sus datos
    tiendas = [
        {
            'nombre': 'Doña Filomena',
            'contacto': 'Filomena Salgado',
            'direccion': 'Calle La Tablada #4513',
            'telefono': '71234567',
            'pedido': '1001',
            'foto': 'tienda_barrio.jpg',
            'ubicacion': [-17.3935, -66.1578]
        },
        {
            'nombre': 'Abarrotes El Carmen',
            'contacto': 'Carmen Rojas',
            'direccion': 'Av. Blanco Galindo Km 2',
            'telefono': '72345678',
            'pedido': '1002',
            'foto': 'tienda_carmen.jpg',
            'ubicacion': [-17.3850, -66.1700]
        },
        {
            'nombre': 'Minimarket Los Andes',
            'contacto': 'Juan Mamani',
            'direccion': 'Av. Aroma Este #345',
            'telefono': '73456789',
            'pedido': '1003',
            'foto': 'tienda_andes.jpg',
            'ubicacion': [-17.3900, -66.1420]
        },
        {
            'nombre': 'Tienda Don Pedro',
            'contacto': 'Pedro Flores',
            'direccion': 'Calle Jordan #1234',
            'telefono': '71234567',
            'pedido': '1004',
            'foto': 'tienda_pedro.jpg',
            'ubicacion': [-17.3890, -66.1610]
        },
        {
            'nombre': 'Mercadito Central',
            'contacto': 'Maria Gutierrez',
            'direccion': 'Av. Ayacucho #887',
            'telefono': '79012345',
            'pedido': '1004',
            'foto': 'tienda_central.jpg',
            'ubicacion': [-17.3925, -66.1480]
        },
        {
            'nombre': 'Almacén El Sol',
            'contacto': 'Luis Mendoza',
            'direccion': 'Av. Heroinas #765',
            'telefono': '76789012',
            'pedido': '1005',
            'foto': 'tienda_sol.jpg',
            'ubicacion': [-17.3800, -66.1550]
        },
        {
            'nombre': 'Tienda Doña Rosa',
            'contacto': 'Rosa Mamani',
            'direccion': 'Calle Sucre #432',
            'telefono': '75678901',
            'pedido': '1006',
            'foto': 'tienda_rosa.jpg',
            'ubicacion': [-17.4010, -66.1520]
        }
    ]

    # Agregar marcadores para cada tienda
    for tienda in tiendas:
        foto_url = url_for('static', filename=f"fotos/{tienda['foto']}")

        popup_content = f"""
        <table border='1' class='table table-success table-striped'>
            <thead>
                <tr><td colspan='2'><img src='{foto_url}' width='100' alt='Foto'></td></tr>
                <tr><td colspan='2'><b>{tienda['nombre']}</b></td></tr>
            </thead>
            <tbody>
                <tr><td><b>Contacto:</b></td><td>{tienda['contacto']}</td></tr>
                <tr><td><b>Dirección:</b></td><td>{tienda['direccion']}</td></tr>
                <tr><td><b>Teléfono:</b></td><td>{tienda['telefono']}</td></tr>
                <tr><td style='color:green' colspan='2'><center><a class='btn btn-primary' href='/pedido?
style='color:green'>Ver Pedido #{tienda['pedido']}</a></center></td></tr>
            </tbody>
        </table>
        """

        folium.Marker(
            location=tienda['ubicacion'],
            popup=folium.Popup(popup_content, max_width=300),
            tooltip=tienda['nombre'],
            icon=folium.Icon(color='blue', icon='shopping-cart', prefix='fa')
        ).add_to(m)

    # Guardar el mapa en un archivo HTML
    mapa_html_path = 'mapa.html'
    # m.save('static/mapa_con_ruta.html')

    # mapa_html_path = 'mapa_con_ruta.html'

    # return render_template('mapa.html', mapa_file=mapa_html_path)

    # Renderizar la plantilla HTML
    return render_template('mapa.html', mapa=m._repr_html_())

@app.route('/pedido')
def ver_pedido():
    if 'username' not in session or session['username'] == None:
        return redirect(url_for('login'))
    return render_template('pedido.html')


@app.route('/buscar_pedido', methods=['GET', 'POST'])
def buscar_pedido():
    pedido = None
    error = None
    success = None
    total = 0

    if request.method == 'POST':
        numero_pedido = request.form.get('numero_pedido', '').strip().upper()

        if not numero_pedido:
            error = "Por favor, ingrese un número de pedido."
        elif numero_pedido in PEDIDOS_DB:
            pedido = PEDIDOS_DB[numero_pedido]
            # Calcular total
            total = sum([art['cantidad'] * art['precio'] for art in pedido['articulos']])
        else:
            error = f"El pedido '{numero_pedido}' no existe en el sistema."

    return render_template('pedido.html',
                             pedido=pedido,
                             error=error,
                             success=success,
                             total=total,
                             pedidos_existentes=True)

@app.route('/actualizar_pedido', methods=['POST'])
def actualizar_pedido():
    numero_pedido = request.form['numero_pedido']
    if numero_pedido in PEDIDOS_DB:
        pedido = PEDIDOS_DB[numero_pedido]
        return render_template('pedido.html',
                             error="Pedido no encontrado.")

    # Actualizar articulos
    pedido = PEDIDOS_DB[numero_pedido]

    try:
        for articulo in pedido['articulos']:
            articulo_id = str(articulo['id'])
            articulo['nombre'] = request.form.get(f'nombre_{articulo_id}', '').strip()
            articulo['cantidad'] = int(request.form.get(f'cantidad_{articulo_id}', 0))
            articulo['precio'] = float(request.form.get(f'precio_{articulo_id}', 0.0))

        # Validaciones básicas
            if not articulo['nombre']:
                raise ValueError("El nombre del articulo no puede estar vacio.")
            if articulo['cantidad'] <= 0:
                raise ValueError("La cantidad debe ser mayor a cero.")
            if articulo['precio'] < 0:
                raise ValueError("El precio no puede ser negativo.")

        # Calcular nuevo total
        total = sum([art['cantidad'] * art['precio'] for art in pedido['articulos']])

        return render_template('pedido.html',
                                 pedido=pedido,
                                 success="Pedido actualizado correctamente.",
                                 total=total)

    except (ValueError, TypeError) as e:
        return render_template('pedido2.html',
                                 pedido=pedido,
                                 error=f"Error al actualizar: {str(e)}",
                                 total=sum([art['cantidad'] * art['precio'] for art in
                                 pedido['articulos']]))