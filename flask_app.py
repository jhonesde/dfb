from flask import Flask, render_template, request, redirect, url_for, session, flash
from functools import wraps
import json
import datetime
import uuid # Necesario para generar IDs únicos de pedido

# --- ESTRATEGIA DE LOGGING FINAL ---
app = Flask(__name__)
app.secret_key = "tu_clave_secreta_muy_segura" 
app.logger.error("--- DEBUG [FINAL]: 0. App de Flask INICIADA. ---")

import folium

# --- INTENTO DE IMPORTAR OSMNX (RUTEO) ---
try:
    import osmnx as ox
    import networkx as nx
    app.logger.error("--- DEBUG [FINAL]: 0.5. 'import osmnx' - ¡ÉXITO! ---")
except Exception as e:
    ox = None
    app.logger.error(f"--- DEBUG [FINAL]: 0.5. ERROR AL IMPORTAR OSMNX: {e} ---")

G_cochabamba = None 

# --- AÑADIDO PARA FIREBASE ---
try:
    import firebase_admin
    from firebase_admin import credentials, firestore
    app.logger.error("--- DEBUG [FINAL]: 1. 'import firebase_admin' - ¡ÉXITO! ---")
except Exception as e:
    app.logger.error(f"--- DEBUG [FINAL]: 1.5. ERROR AL IMPORTAR firebase_admin: {e} ---")

# --- INICIALIZACIÓN DE FIREBASE ---
db = None 
try:
    app.logger.error("--- DEBUG [FINAL]: 2. Intentando inicializar Firebase... ---")
    ruta_llave = '/home/AllenR/mysite/serviceAccountKey.json'
    cred = credentials.Certificate(ruta_llave)
    firebase_admin.initialize_app(cred)
    db = firestore.client()
    app.logger.error("--- DEBUG [FINAL]: 3. Conexión a Firestore establecida. ¡ÉXITO! ---")
except ValueError:
    pass 
except Exception as e:
    app.logger.error(f"--- DEBUG [FINAL]: 4. ERROR CRÍTICO AL INICIAR FIREBASE: {e} ---")


def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'username' not in session:
            flash('Debes iniciar sesión.', 'error')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

@app.route('/')
def home():
    return render_template('home.html')

# --- NUEVO: REGISTRO PÚBLICO ---
@app.route('/registro_cliente', methods=['GET', 'POST'])
def registro_cliente():
    if request.method == 'POST':
        username = request.form['username'].strip()
        password = request.form['password']
        nombre_completo = request.form['nombre'].strip()
        
        try:
            doc_ref = db.collection('usuarios').document(username)
            if doc_ref.get().exists:
                flash('El usuario ya existe.', 'error')
            else:
                # GUARDADO EN FIREBASE CON ROL 'CLIENTE'
                doc_ref.set({
                    'password': password,
                    'role': 'cliente',
                    'nombre_completo': nombre_completo,
                    'telefono': request.form.get('telefono', ''),
                    'direccion': request.form.get('direccion', ''),
                    'ciudad': request.form.get('ciudad', ''),
                })
                flash('Cuenta creada. Inicia sesión.', 'success')
                return redirect(url_for('login'))
        except Exception as e:
            flash(f'Error al registrar: {e}', 'error')
            
    return render_template('registro_cliente.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        try:
            doc_ref = db.collection('usuarios').document(username).get()
            if doc_ref.exists:
                user_data = doc_ref.to_dict()
                if user_data.get('password') == password:
                    session['username'] = username
                    session['role'] = user_data.get('role') 
                    session['nombre_completo'] = user_data.get('nombre_completo', username)
                    
                    flash(f'Bienvenido, {session.get("nombre_completo", username)}!', 'success')
                    
                    # Redirección inteligente
                    if session['role'] == 'cliente':
                        return redirect(url_for('portal_cliente'))
                    else:
                        return redirect(url_for('dashboard'))
                else:
                    flash('Contraseña incorrecta', 'error')
            else:
                flash('Usuario no encontrado', 'error')
        except Exception as e:
            app.logger.error(f"Login error: {e}")
            flash('Error de conexión con Firestore', 'error')
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    flash('Sesión cerrada.', 'info')
    return redirect(url_for('home'))

@app.route('/dashboard')
@login_required
def dashboard():
    # Redirección de seguridad: Si es cliente, va a su portal
    if session.get('role') == 'cliente':
        return redirect(url_for('portal_cliente'))
    
    return render_template('dashboard.html')

# --- NUEVO: PORTAL CLIENTE (FILTRADO) ---
@app.route('/portal_cliente')
@login_required
def portal_cliente():
    if session['role'] != 'cliente':
        return redirect(url_for('dashboard'))
        
    mis_pedidos = []
    try:
        # Buscamos solo los pedidos creados por este usuario
        docs = db.collection('pedidos').where(field_path='usuario_creador', op_string='==', value=session['username']).stream()
        for doc in docs:
            p = doc.to_dict()
            p['numero'] = doc.id
            total = sum([float(a.get('cantidad',0))*float(a.get('precio',0)) for a in p.get('articulos', [])])
            p['total_calculado'] = total
            mis_pedidos.append(p)
    except Exception as e:
        app.logger.error(f"Error en portal_cliente: {e}")
        flash('Error al cargar sus pedidos.', 'error')
    
    return render_template('portal_cliente.html', pedidos=mis_pedidos)


@app.route('/gestionar_usuarios', methods=['GET', 'POST'])
@login_required
def gestionar_usuarios():
    if session['role'] not in ['admin', 'editor']: return redirect(url_for('dashboard'))

    if request.method == 'POST':
        username = request.form['username'].strip()
        password = request.form['password']
        role = request.form['role']
        try:
            doc_ref = db.collection('usuarios').document(username)
            if doc_ref.get().exists: flash('El usuario ya existe.', 'error')
            else:
                doc_ref.set({'password': password, 'role': role})
                flash(f'Usuario {username} creado.', 'success')
        except Exception as e: flash(f'Error: {e}', 'error')
        return redirect(url_for('gestionar_usuarios'))

    lista_usuarios = []
    try:
        docs = db.collection('usuarios').stream()
        for doc in docs:
            u = doc.to_dict(); u['username'] = doc.id; lista_usuarios.append(u)
    except: pass
    return render_template('gestionar_usuarios.html', usuarios=lista_usuarios)

@app.route('/borrar_usuario/<username>', methods=['POST'])
@login_required
def borrar_usuario(username):
    if session['role'] not in ['admin', 'editor']: return redirect(url_for('dashboard'))
    if username == session['username']: return redirect(url_for('gestionar_usuarios'))
    try: db.collection('usuarios').document(username).delete()
    except: pass
    return redirect(url_for('gestionar_usuarios'))

# --- GESTIÓN DE PRODUCTOS ---
@app.route('/gestionar_productos', methods=['GET', 'POST'])
@login_required
def gestionar_productos():
    if session['role'] not in ['admin', 'editor']: return redirect(url_for('dashboard'))
    
    if request.method == 'POST':
        nombre_prod = request.form['nombre'].strip()
        precio = float(request.form['precio'])
        stock_inicial = int(request.form['stock'])
        try:
            doc_ref = db.collection('productos').document(nombre_prod)
            doc_ref.set({'nombre': nombre_prod, 'precio': precio, 'stock': stock_inicial}, merge=True)
            flash(f'Producto "{nombre_prod}" guardado.', 'success')
        except Exception as e: flash(f'Error: {e}', 'error')
        return redirect(url_for('gestionar_productos'))

    lista_productos = []
    try:
        docs = db.collection('productos').stream()
        for doc in docs:
            p = doc.to_dict(); p['id'] = doc.id; lista_productos.append(p)
    except: pass
    return render_template('gestionar_productos.html', productos=lista_productos)

@app.route('/actualizar_stock/<producto_id>', methods=['POST'])
@login_required
def actualizar_stock(producto_id):
    if session['role'] not in ['admin', 'editor']: return redirect(url_for('dashboard'))
    try:
        db.collection('productos').document(producto_id).update({'stock': int(request.form['nuevo_stock'])})
        flash('Stock actualizado.', 'success')
    except Exception as e: flash(f'Error: {e}', 'error')
    return redirect(url_for('gestionar_productos'))

@app.route('/borrar_producto/<producto_id>', methods=['POST'])
@login_required
def borrar_producto(producto_id):
    if session['role'] not in ['admin', 'editor']: return redirect(url_for('dashboard'))
    try:
        db.collection('productos').document(producto_id).delete()
        flash('Producto eliminado.', 'success')
    except: flash('Error al eliminar.', 'error')
    return redirect(url_for('gestionar_productos'))

# --- BORRAR PEDIDO ---
@app.route('/borrar_pedido/<numero_pedido>', methods=['POST'])
@login_required
def borrar_pedido(numero_pedido):
    if session['role'] not in ['admin', 'editor']: return redirect(url_for('reporte_pedidos'))

    try:
        db.collection('pedidos').document(numero_pedido).delete()
        flash(f'Pedido {numero_pedido} eliminado correctamente.', 'success')
    except Exception as e:
        flash(f'Error al eliminar pedido: {e}', 'error')
        
    return redirect(url_for('reporte_pedidos'))

# --- CREAR PEDIDO (INTELIGENTE) ---
@app.route('/crear_pedido', methods=['GET', 'POST'])
@login_required
def crear_pedido():
    if session['role'] not in ['admin', 'editor', 'cliente']:
        return redirect(url_for('dashboard'))

    if request.method == 'POST':
        try:
            # 1. Asignar ID y Nombre (Lógica de Cliente vs Admin)
            if session['role'] == 'cliente':
                suffix = datetime.datetime.now().strftime("%Y%m%d%H%M")
                numero_pedido = f"CLI-{suffix}"
                cliente_nombre = request.form['cliente_nombre_hidden']
            else:
                numero_pedido = request.form['numero_pedido'].strip().upper()
                cliente_nombre = request.form['cliente']

            ids_productos = request.form.getlist('item_nombre[]')
            cantidades = request.form.getlist('item_cantidad[]')
            precios_inputs = request.form.getlist('item_precio_hidden[]')
            articulos_para_guardar = []
            
            # 2. Validar y Descontar Stock
            for i in range(len(ids_productos)):
                prod_id = ids_productos[i]
                if not prod_id: continue
                cant = int(cantidades[i])
                precio_unitario = float(precios_inputs[i])

                doc_prod = db.collection('productos').document(prod_id).get()
                data = doc_prod.to_dict()
                
                if data.get('stock', 0) < cant:
                    flash(f'Stock insuficiente ({data.get("stock", 0)}) para {prod_id}.', 'error')
                    productos_disponibles = [d.to_dict() for d in db.collection('productos').stream()]
                    fecha_hoy = request.form['fecha']
                    return render_template('crear_pedido.html', fecha_hoy=fecha_hoy, productos=productos_disponibles, error_stock=True)
                
                articulos_para_guardar.append({
                    'id': i+1, 'nombre': prod_id, 'cantidad': cant, 'precio': precio_unitario
                })
                # Descontar stock
                db.collection('productos').document(prod_id).update({'stock': firestore.Increment(-cant)})

            # 3. Guardar Pedido
            nuevo_pedido = {
                'cliente': cliente_nombre,
                'usuario_creador': session['username'],
                'telefono': request.form['telefono'],
                'fecha': request.form['fecha'],
                'direccion': request.form['direccion'],
                'ciudad': request.form['ciudad'],
                'estado': 'Pendiente',
                'articulos': articulos_para_guardar
            }
            db.collection('pedidos').document(numero_pedido).set(nuevo_pedido)
            
            if session['role'] == 'cliente':
                flash(f'¡Pedido enviado! Su ID es {numero_pedido}.', 'success')
                return redirect(url_for('portal_cliente'))
            else:
                flash(f'Pedido {numero_pedido} creado.', 'success')
                return redirect(url_for('dashboard'))

        except Exception as e:
            flash(f'Error al procesar el pedido: {e}', 'error')

    # GET
    productos_disponibles = [d.to_dict() for d in db.collection('productos').stream()]
    fecha_hoy = datetime.date.today().strftime('%Y-%m-%d')
    return render_template('crear_pedido.html', fecha_hoy=fecha_hoy, productos=productos_disponibles)

# --- RUTA DE ASIGNACIÓN ---
@app.route('/asignar_conductor', methods=['POST'])
@login_required
def asignar_conductor():
    if session['role'] not in ['admin', 'editor']: return redirect(url_for('reporte_pedidos'))
    
    numero_pedido = request.form.get('numero_pedido')
    driver_username = request.form.get('driver')
    
    try:
        db.collection('pedidos').document(numero_pedido).update({
            'driver_asignado': driver_username,
            'estado': 'En reparto'
        })
        flash(f'Pedido {numero_pedido} asignado a {driver_username} y marcado como "En reparto".', 'success')
    except Exception as e:
        flash(f'Error al asignar: {e}', 'error')
        
    return redirect(url_for('reporte_pedidos'))

# --- RUTA CRÍTICA: ACTUALIZAR ESTADO A ENTREGADO ---
@app.route('/actualizar_estado_pedido', methods=['POST'])
@login_required
def actualizar_estado_pedido():
    # Permitido para Admin, Editor, y Drivers
    if session['role'] not in ['admin', 'editor', 'driver']:
        flash('No tienes permiso para actualizar el estado.', 'error')
        return redirect(url_for('reporte_pedidos'))
        
    numero_pedido = request.form.get('numero_pedido')
    
    nuevo_estado = 'Entregado'
    
    try:
        pedido_doc = db.collection('pedidos').document(numero_pedido).get()
        pedido_data = pedido_doc.to_dict()
        
        # Validación de permiso si es driver
        if session['role'] == 'driver':
            if pedido_data.get('driver_asignado') != session['username']:
                flash('No tiene permiso para actualizar este pedido.', 'error')
                return redirect(url_for('reporte_pedidos'))
            
        db.collection('pedidos').document(numero_pedido).update({
            'estado': nuevo_estado,
            'fecha_entrega_real': datetime.date.today().strftime('%Y-%m-%d')
        })
        
        flash(f'Pedido {numero_pedido} marcado como "Entregado".', 'success')
    except Exception as e:
        flash(f'Error al marcar como entregado: {e}', 'error')
        
    return redirect(url_for('reporte_pedidos'))

# --- REPORTE DE PEDIDOS ---
@app.route('/reporte_pedidos')
@login_required
def reporte_pedidos():
    if session['role'] not in ['admin', 'editor', 'driver']: return redirect(url_for('dashboard'))

    pedidos_lista = []
    total_global = 0
    drivers_lista = [] 
    
    try:
        docs = db.collection('pedidos').stream()
        
        for doc in docs:
            p = doc.to_dict()
            p['numero'] = doc.id
            
            if session['role'] == 'driver':
                if p.get('driver_asignado') != session['username']:
                    continue 
            
            total_pedido = sum([float(a.get('cantidad', 0)) * float(a.get('precio', 0)) for a in p.get('articulos', [])])
            p['total_calculado'] = total_pedido
            total_global += total_pedido
            pedidos_lista.append(p)
            
        if session['role'] in ['admin', 'editor']:
            usuarios = db.collection('usuarios').where(field_path='role', op_string='==', value='driver').stream()
            for u in usuarios:
                drivers_lista.append(u.id)

    except Exception as e:
        app.logger.error(f"Error reportes: {e}")
        flash('Error al cargar la lista de pedidos.', 'error')

    return render_template('reporte_pedidos.html', 
                           pedidos=pedidos_lista, 
                           total_global=total_global,
                           drivers=drivers_lista) 

# --- MAPA ---
@app.route('/ver_mapa')
def ver_mapa():
    if 'username' not in session: return redirect(url_for('login'))
    # Lógica de mapa y ruteo...
    return render_template('mapa.html', mapa="")

@app.route('/pedido')
def ver_pedido():
    if 'username' not in session: return redirect(url_for('login'))
    return render_template('pedido.html')

@app.route('/buscar_pedido', methods=['POST'])
def buscar_pedido():
    numero = request.form.get('numero_pedido', '').strip().upper()
    try:
        doc = db.collection('pedidos').document(numero).get()
        if doc.exists:
            p = doc.to_dict(); p['numero'] = doc.id
            total = sum([a.get('cantidad', 0)*a.get('precio', 0) for a in p.get('articulos', [])])
            return render_template('pedido.html', pedido=p, success="Encontrado", total=total)
        else: return render_template('pedido.html', error="No encontrado")
    except Exception as e: return render_template('pedido.html', error=str(e))

@app.route('/actualizar_pedido', methods=['POST'])
def actualizar_pedido():
    numero = request.form['numero_pedido']
    try:
        doc_ref = db.collection('pedidos').document(numero)
        p_data = doc_ref.get().to_dict()
        if 'articulos' in p_data:
             for articulo in p_data['articulos']:
                aid = str(articulo.get('id'))
                if not aid: continue
                articulo['nombre'] = request.form.get(f'nombre_{aid}', '').strip()
                articulo['cantidad'] = int(request.form.get(f'cantidad_{aid}', 0))
                articulo['precio'] = float(request.form.get(f'precio_{aid}', 0.0))
        
        doc_ref.update({'articulos': p_data['articulos']}) 
        total = sum([float(art['cantidad']) * float(art['precio']) for art in p_data.get('articulos', [])])
        return render_template('pedido.html', pedido=p_data, success="Actualizado", total=total)
    except Exception as e: return render_template('pedido.html', error=str(e))

if __name__ == '__main__':
    app.run(debug=True)