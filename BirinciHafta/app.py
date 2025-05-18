from flask import Flask, render_template, redirect, url_for, request, flash
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user

app = Flask(__name__)
app.config['SECRET_KEY'] = 'cok_gizli_anahtar'  
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///kullanici.db'  
db = SQLAlchemy(app)


login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'giris_sayfasi'


class Kullanici(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    kullanici_adi = db.Column(db.String(80), unique=True, nullable=False)
    sifre = db.Column(db.String(200), nullable=False)

@login_manager.user_loader
def load_user(user_id):
    return Kullanici.query.get(int(user_id))


@app.route('/')
def index():
    return render_template("anasayfa.html")


@app.route('/kayit_ekrani.html', methods=['GET', 'POST'])
def kayit_ekrani():
    if request.method == 'POST':
        kullanici_adi = request.form['kullanici_adi']
        sifre = request.form['sifre']
        
        if Kullanici.query.filter_by(kullanici_adi=kullanici_adi).first():
            flash('Bu kullanıcı adı zaten alınmış!', 'hata')
            return redirect(url_for('kayit_ekrani'))
        
        yeni_kullanici = Kullanici(
            kullanici_adi=kullanici_adi,
            sifre=generate_password_hash(sifre, method='pbkdf2:sha256')
        )
        db.session.add(yeni_kullanici)
        db.session.commit()
        
        flash('Kayıt başarılı! Giriş yapabilirsiniz.', 'basarili')
        return redirect(url_for('giris_sayfasi'))
    
    return render_template("kayit_ekrani.html")

@app.route('/giris_sayfasi.html', methods=['GET', 'POST'])
def giris_sayfasi():
    if request.method == 'POST':
        kullanici_adi = request.form['kullanici_adi']
        sifre = request.form['sifre']
        kullanici = Kullanici.query.filter_by(kullanici_adi=kullanici_adi).first()
        
        if kullanici and check_password_hash(kullanici.sifre, sifre):
            login_user(kullanici)
            return redirect(url_for('anasayfa'))
        else:
            flash('Kullanıcı adı veya şifre hatalı!', 'hata')
    
    return render_template("giris_sayfasi.html")

@app.route('/cikis_ekrani.html')
@login_required
def cikis_ekrani():
    logout_user()
    return redirect(url_for('index'))


@app.route('/ogrenciler.html')
@login_required
def anasayfa():
    return render_template("ogrenciler.html", kullanici=current_user)

@app.route('/dersler.html')
@login_required
def dersler():
    return render_template("dersler.html")

@app.route('/notlar.html')
@login_required
def notlar():
    return render_template('/notlar.html')

@app.route('/raporlar.html')
@login_required
def raporlar():
    return render_template('/raporlar.html')

with app.app_context():
    db.create_all()

if __name__ == "__main__":
    app.run(debug=True)