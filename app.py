from flask import Flask, render_template, request, redirect, session, url_for
import sqlite3
import os
import time

app = Flask(__name__)
app.secret_key = "chave_super_secreta_e_segura_do_louvemos_digital"

DATABASE = 'louvemos.db'

def obter_conexao():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn

def iniciar_banco():
    conn = obter_conexao()
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS musicas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            titulo TEXT NOT NULL,
            artista TEXT NOT NULL,
            tom_original TEXT NOT NULL,
            letra TEXT NOT NULL
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS listas_repertorio (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nome TEXT NOT NULL
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS lista_musica (
            lista_id INTEGER,
            musica_id INTEGER,
            PRIMARY KEY (lista_id, musica_id),
            FOREIGN KEY (lista_id) REFERENCES listas_repertorio(id) ON DELETE CASCADE,
            FOREIGN KEY (musica_id) REFERENCES musicas(id) ON DELETE CASCADE
        )
    ''')
    conn.commit()
    conn.close()

iniciar_banco()

@app.route('/')
def index():
    conn = obter_conexao()
    musicas = conn.execute('SELECT * FROM musicas ORDER BY titulo').fetchall()
    listas = conn.execute('SELECT * FROM listas_repertorio ORDER BY id DESC').fetchall()
    conn.close()
    versao_fundo = int(time.time())
    return render_template('index.html', musicas=musicas, listas=listas, versao_fundo=versao_fundo)

@app.route('/musica/<int:id>')
def ver_musica(id):
    conn = obter_conexao()
    musica = conn.execute('SELECT * FROM musicas WHERE id = ?', (id,)).fetchone()
    conn.close()
    if not musica: return "Música não encontrada!", 404
    versao_fundo = int(time.time())
    return render_template('musica.html', musica=musica, versao_fundo=versao_fundo)

@app.route('/lista/criar', methods=['POST'])
def criar_lista():
    nome = request.form.get('nome', '').strip()
    if nome:
        conn = obter_conexao()
        conn.execute('INSERT INTO listas_repertorio (nome) VALUES (?)', (nome,))
        conn.commit()
        conn.close()
    return redirect(url_for('index'))

@app.route('/lista/<int:id>')
def ver_lista(id):
    conn = obter_conexao()
    lista = conn.execute('SELECT * FROM listas_repertorio WHERE id = ?', (id,)).fetchone()
    if not lista:
        conn.close()
        return "Repertório não encontrado!", 404
    musicas_na_lista = conn.execute('''
        SELECT m.* FROM musicas m 
        JOIN lista_musica lm ON m.id = lm.musica_id 
        WHERE lm.lista_id = ? ORDER BY m.titulo
    ''', (id,)).fetchall()
    todas_musicas = conn.execute('SELECT id, titulo, artista FROM musicas ORDER BY titulo').fetchall()
    conn.close()
    versao_fundo = int(time.time())
    return render_template('lista.html', lista=lista, musicas_na_lista=musicas_na_lista, todas_musicas=todas_musicas, versao_fundo=versao_fundo)

@app.route('/lista/editar_nome/<int:id>', methods=['POST'])
def editar_nome_lista(id):
    novo_nome = request.form.get('nome', '').strip()
    if novo_nome:
        conn = obter_conexao()
        conn.execute('UPDATE listas_repertorio SET nome = ? WHERE id = ?', (novo_nome, id))
        conn.commit()
        conn.close()
    return redirect(url_for('ver_lista', id=id))

@app.route('/lista/excluir/<int:id>')
def excluir_lista(id):
    conn = obter_conexao()
    conn.execute('DELETE FROM listas_repertorio WHERE id = ?', (id,))
    conn.execute('DELETE FROM lista_musica WHERE lista_id = ?', (id,))
    conn.commit()
    conn.close()
    return redirect(url_for('index'))

@app.route('/lista/<int:lista_id>/add_musica', methods=['POST'])
def add_musica_na_lista(lista_id):
    musica_id = request.form.get('musica_id')
    if musica_id:
        conn = obter_conexao()
        try:
            conn.execute('INSERT INTO lista_musica (lista_id, musica_id) VALUES (?, ?)', (lista_id, musica_id))
            conn.commit()
        except sqlite3.IntegrityError: pass 
        conn.close()
    return redirect(url_for('ver_lista', id=lista_id))

@app.route('/lista/<int:lista_id>/remove_musica/<int:musica_id>')
def remove_musica_da_lista(lista_id, musica_id):
    conn = obter_conexao()
    conn.execute('DELETE FROM lista_musica WHERE lista_id = ? AND musica_id = ?', (lista_id, musica_id))
    conn.commit()
    conn.close()
    return redirect(url_for('ver_lista', id=lista_id))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        senha = request.form.get('senha')
        if senha == 'admin123':  
            session['admin'] = True
            return redirect(url_for('admin'))
        return render_template('login.html', erro="Senha incorreta!")
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.pop('admin', None)
    return redirect(url_for('index'))

@app.route('/admin/upload_fundo', methods=['POST'])
def upload_fundo():
    if not session.get('admin'): return redirect(url_for('login'))
    pasta_static = os.path.join(app.root_path, 'static')
    if not os.path.exists(pasta_static): os.makedirs(pasta_static)
    if 'foto_fundo_claro' in request.files:
        arq_claro = request.files['foto_fundo_claro']
        if arq_claro.filename != '': arq_claro.save(os.path.join(pasta_static, 'fundo.png'))
    if 'foto_fundo_escuro' in request.files:
        arq_escuro = request.files['foto_fundo_escuro']
        if arq_escuro.filename != '': arq_escuro.save(os.path.join(pasta_static, 'fundo_escuro.png'))
    return redirect(url_for('admin'))

@app.route('/admin')
def admin():
    if not session.get('admin'): return redirect(url_for('login'))
    conn = obter_conexao()
    musicas = conn.execute('SELECT * FROM musicas ORDER BY titulo').fetchall()
    musica_editando = None
    editar_id = request.args.get('editar_id')
    if editar_id:
        musica_editando = conn.execute('SELECT * FROM musicas WHERE id = ?', (editar_id,)).fetchone()
    conn.close()
    return render_template('admin.html', musicas=musicas, musica_editando=musica_editando)

@app.route('/admin/adicionar', methods=['POST'])
def adicionar():
    if not session.get('admin'): return redirect(url_for('login'))
    titulo = request.form['titulo']
    artista = request.form['artista']
    tom_original = request.form['tom_original']
    letra_bruta = request.form['letra'].replace('\r\n', '\n')
    
    conn = obter_conexao()
    conn.execute('INSERT INTO musicas (titulo, artista, tom_original, letra) VALUES (?, ?, ?, ?)',
                 (titulo, artista, tom_original, letra_bruta))
    conn.commit()
    conn.close()
    return redirect(url_for('admin'))

@app.route('/admin/editar/<int:id>', methods=['POST'])
def editar(id):
    if not session.get('admin'): return redirect(url_for('login'))
    titulo = request.form['titulo']
    artista = request.form['artista']
    tom_original = request.form['tom_original']
    letra_bruta = request.form['letra'].replace('\r\n', '\n')
    
    conn = obter_conexao()
    conn.execute('UPDATE musicas SET titulo=?, artista=?, tom_original=?, letra=? WHERE id=?',
                 (titulo, artista, tom_original, letra_bruta, id))
    conn.commit()
    conn.close()
    return redirect(url_for('admin'))

@app.route('/admin/excluir/<int:id>')
def excluir(id):
    if not session.get('admin'): return redirect(url_for('login'))
    conn = obter_conexao()
    conn.execute('DELETE FROM musicas WHERE id=?', (id,))
    conn.execute('DELETE FROM lista_musica WHERE musica_id=?', (id,))
    conn.commit()
    conn.close()
    return redirect(url_for('admin'))

if __name__ == '__main__':
    app.run(debug=True)