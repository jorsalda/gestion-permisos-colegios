import password
from flask import Flask, render_template, request, redirect, url_for, flash
git add
# 🔐 Configuración de Flask-Login
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'  # Redirige a /login si no está autenticado


@login_manager.user_loader
def load_user(user_id):
    return Usuario.query.get(int(user_id))


# 🏠 Ruta principal
@app.route('/')
def index():
    return redirect(url_for('formulario'))


# 🔑 Registro de nuevo colegio + usuario
@app.route('/register', methods=['GET', 'POST'])
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        colegio_nombre = request.form['colegio'].strip()

        if not email or not password or not colegio_nombre:
            flash("❌ Todos los campos son obligatorios", "danger")
            return render_template('register.html')

        # Verificar si el colegio ya existe
        colegio = Colegio.query.filter_by(nombre=colegio_nombre).first()
        if not colegio:
            colegio = Colegio(nombre=colegio_nombre)
            db.session.add(colegio)
            db.session.commit()

        # Verificar si el email ya está registrado
        if Usuario.query.filter_by(email=email).first():
            flash("❌ Este correo ya está registrado", "danger")
            return render_template('register.html')

        # ✅ Hashear la contraseña con pbkdf2:sha256 (compatible con todas las versiones)
        usuario = Usuario(
            email=email,
            password_hash=generate_password_hash(password, method='pbkdf2:sha256', salt_length=8),
            colegio_id=colegio.id
        )
        db.session.add(usuario)
        db.session.commit()
        flash("✅ Registro exitoso. Ahora inicia sesión.", "success")
        return redirect(url_for('login'))

    return render_template('register.html')


# 🔑 Inicio de sesión
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        usuario = Usuario.query.filter_by(email=email).first()
        if usuario and check_password_hash(usuario.password_hash, password):
            login_user(usuario)
            return redirect(url_for('formulario'))
        else:
            flash("❌ Email o contraseña incorrectos", "danger")
    return render_template('login.html')


# 🚪 Cerrar sesión
@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))


# 📝 Formulario principal (PROTEGIDO)
@app.route('/formulario', methods=['GET', 'POST'])
@login_required
def formulario():
    docentes = Docente.query.filter_by(colegio_id=current_user.colegio_id).all()
    tipos = ['Vacaciones', 'Enfermedad', 'Permiso Personal', 'Capacitación', 'Otro']

    docente_seleccionado = None
    historial = []

    if request.method == 'POST':
        # Guardar nuevo permiso
        if 'guardar' in request.form:
            docente_id = request.form['docente']
            fecha_inicio = request.form['fecha_inicio']
            fecha_fin = request.form['fecha_fin']
            tipo = request.form['tipo']
            observacion = request.form.get('observacion', '')

            nuevo_permiso = Permiso(
                docente_id=docente_id,
                fecha_inicio=fecha_inicio,
                fecha_fin=fecha_fin,
                tipo=tipo,
                observacion=observacion,
                colegio_id=current_user.colegio_id  # ← ¡Importante!
            )
            db.session.add(nuevo_permiso)
            db.session.commit()
            flash("✅ Permiso guardado correctamente", "success")
            return redirect(url_for('listado'))

        # Ver historial
        elif 'ver_historial' in request.form:
            docente_id = request.form['docente']
            docente_seleccionado = Docente.query.get(docente_id)
            if docente_seleccionado:
                historial = (
                    Permiso.query
                    .filter_by(docente_id=docente_id, colegio_id=current_user.colegio_id)
                    .order_by(Permiso.fecha_inicio.desc())
                    .all()
                )

    return render_template(
        'formulario.html',
        docentes=docentes,
        tipos=tipos,
        docente_seleccionado=docente_seleccionado,
        historial=historial
    )


# 📋 Listado de permisos (PROTEGIDO)
@app.route('/listado')
@login_required
def listado():
    permisos = Permiso.query.filter_by(colegio_id=current_user.colegio_id).all()
    return render_template('permisos.html', permisos=permisos)

# 👥 Gestión de docentes (PROTEGIDO)
@app.route('/docentes')
@login_required
def listar_docentes():
    docentes = Docente.query.filter_by(colegio_id=current_user.colegio_id).all()
    return render_template('docentes.html', docentes=docentes)


@app.route('/docente/nuevo', methods=['GET', 'POST'])
@login_required
def nuevo_docente():
    if request.method == 'POST':
        nombre = request.form['nombre'].strip()
        if nombre:
            nuevo = Docente(nombre=nombre, colegio_id=current_user.colegio_id)
            db.session.add(nuevo)
            db.session.commit()
            flash("✅ Docente agregado correctamente", "success")
        else:
            flash("❌ El nombre no puede estar vacío", "danger")
        return redirect(url_for('listar_docentes'))
    return render_template('docente_form.html', docente=None)


@app.route('/docente/editar/<int:id>', methods=['GET', 'POST'])
@login_required
def editar_docente(id):
    docente = Docente.query.filter_by(id=id, colegio_id=current_user.colegio_id).first_or_404()
    if request.method == 'POST':
        nombre = request.form['nombre'].strip()
        if nombre:
            docente.nombre = nombre
            db.session.commit()
            flash("✅ Docente actualizado correctamente", "success")
        else:
            flash("❌ El nombre no puede estar vacío", "danger")
        return redirect(url_for('listar_docentes'))
    return render_template('docente_form.html', docente=docente)


@app.route('/docente/eliminar/<int:id>', methods=['POST'])
@login_required
def eliminar_docente(id):
    docente = Docente.query.filter_by(id=id, colegio_id=current_user.colegio_id).first_or_404()
    if Permiso.query.filter_by(docente_id=id, colegio_id=current_user.colegio_id).first():
        flash("⚠️ No se puede eliminar: el docente tiene permisos registrados.", "warning")
    else:
        db.session.delete(docente)
        db.session.commit()
        flash("🗑️ Docente eliminado correctamente", "success")
    return redirect(url_for('listar_docentes'))


# ✏️ Edición y eliminación de permisos (PROTEGIDO)
@app.route('/permiso/editar/<int:id>', methods=['GET', 'POST'])
@login_required
def editar_permiso(id):
    permiso = Permiso.query.filter_by(id=id, colegio_id=current_user.colegio_id).first_or_404()
    docentes = Docente.query.filter_by(colegio_id=current_user.colegio_id).all()
    tipos = ['Vacaciones', 'Enfermedad', 'Permiso Personal', 'Capacitación', 'Otro']

    if request.method == 'POST':
        permiso.docente_id = request.form['docente']
        permiso.fecha_inicio = request.form['fecha_inicio']
        permiso.fecha_fin = request.form['fecha_fin']
        permiso.tipo = request.form['tipo']
        permiso.observacion = request.form.get('observacion', '')
        db.session.commit()
        flash("✅ Permiso actualizado correctamente", "success")
        return redirect(url_for('listado'))

    return render_template('permiso_form.html', permiso=permiso, docentes=docentes, tipos=tipos)


@app.route('/permiso/eliminar/<int:id>', methods=['POST'])
@login_required
def eliminar_permiso(id):
    permiso = Permiso.query.filter_by(id=id, colegio_id=current_user.colegio_id).first_or_404()
    db.session.delete(permiso)
    db.session.commit()
    flash("🗑️ Permiso eliminado correctamente", "success")
    return redirect(url_for('listado'))

@app.route('/crear-admin')
def crear_admin():
    # Solo para desarrollo — elimínala después
    if Usuario.query.filter_by(email='admin@colegio.com').first():
        return "Ya existe el usuario admin"

    colegio = Colegio(nombre='Colegio Principal')
    db.session.add(colegio)
    db.session.commit()

    usuario = Usuario(
        email='admin@colegio.com',
        password_hash=generate_password_hash(password),
        colegio_id=colegio.id
    )
    db.session.add(usuario)
    db.session.commit()
    return "✅ Usuario admin creado. Email: admin@colegio.com | Contraseña: admin123"




# 🧪 Crear tablas (solo en desarrollo)
with app.app_context():
    db.create_all()

if __name__ == '__main__':
    app.run(debug=True)