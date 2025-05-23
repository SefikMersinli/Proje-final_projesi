from flask import Flask, render_template, redirect, url_for, request, flash
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from datetime import datetime

app = Flask(__name__)
app.config['SECRET_KEY'] = 'cok_gizli_anahtar'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///kullanici.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False 

db = SQLAlchemy(app)

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'giris_sayfasi'

class Kullanici(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    kullanici_adi = db.Column(db.String(80), unique=True, nullable=False)
    sifre = db.Column(db.String(200), nullable=False)
    kisisel_mesaj = db.Column(db.String(500), nullable=True)
    ogrenciler = db.relationship('Ogrenci', backref='ekleyen_kullanici', lazy=True)
    dersler = db.relationship('Ders', backref='ekleyen_kullanici', lazy=True)
    notlar = db.relationship('Not', backref='ekleyen_kullanici', lazy=True)

    def __repr__(self):
        return f"<Kullanici {self.kullanici_adi}>"

class Ogrenci(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    ad = db.Column(db.String(100), nullable=False)
    soyad = db.Column(db.String(100), nullable=False)
    numara = db.Column(db.String(20), unique=True, nullable=False)
    sinif = db.Column(db.String(20), nullable=True)
    dogum_tarihi = db.Column(db.String(10), nullable=True)

    ekleyen_kullanici_id = db.Column(db.Integer, db.ForeignKey('kullanici.id'), nullable=False)
    notlar = db.relationship('Not', backref='ogrenci_bilgi', lazy=True, cascade='all, delete-orphan')

    def __repr__(self):
        return f"<Ogrenci {self.ad} {self.soyad} ({self.numara})>"

class Ders(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    ders_kodu = db.Column(db.String(20), unique=True, nullable=False)
    ders_adi = db.Column(db.String(100), nullable=False)
    kredi = db.Column(db.Integer, nullable=False)
    akts = db.Column(db.Integer, nullable=True)

    ekleyen_kullanici_id = db.Column(db.Integer, db.ForeignKey('kullanici.id'), nullable=False)
    notlar = db.relationship('Not', backref='ders_bilgi', lazy=True, cascade='all, delete-orphan')

    def __repr__(self):
        return f"<Ders {self.ders_kodu} - {self.ders_adi}>"

class Not(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    not_degeri = db.Column(db.Integer, nullable=False)

    ogrenci_id = db.Column(db.Integer, db.ForeignKey('ogrenci.id'), nullable=False)
    ders_id = db.Column(db.Integer, db.ForeignKey('ders.id'), nullable=False)
    ekleyen_kullanici_id = db.Column(db.Integer, db.ForeignKey('kullanici.id'), nullable=False)

    __table_args__ = (db.UniqueConstraint('ogrenci_id', 'ders_id', name='_ogrenci_ders_uc'),)

    def __repr__(self):
        return f"<Not {self.not_degeri} (Ogrenci:{self.ogrenci_bilgi.ad}, Ders:{self.ders_bilgi.ders_adi})>"

@login_manager.user_loader
def load_user(user_id):
    return db.session.get(Kullanici, int(user_id))


@app.route('/')
def index():
    return render_template("anasayfa.html")

@app.route('/kayit_ekrani.html', methods=['GET', 'POST'])
def kayit_ekrani():
    if current_user.is_authenticated:
        return redirect(url_for('anasayfa_kullanici'))

    if request.method == 'POST':
        kullanici_adi = request.form['kullanici_adi']
        sifre = request.form['sifre']

        if Kullanici.query.filter_by(kullanici_adi=kullanici_adi).first():
            flash('Bu kullanıcı adı zaten alınmış!', 'hata')
            return redirect(url_for('kayit_ekrani'))

        yeni_kullanici = Kullanici(
            kullanici_adi=kullanici_adi,
            sifre=generate_password_hash(sifre, method='pbkdf2:sha256'),
            kisisel_mesaj="Henüz size özel bir mesaj yok. Ayarlardan ekleyebilirsiniz!"
        )
        db.session.add(yeni_kullanici)
        db.session.commit()

        flash('Kayıt başarılı! Giriş yapabilirsiniz.', 'basarili')
        return redirect(url_for('giris_sayfasi'))

    return render_template("kayit_ekrani.html")

@app.route('/giris_sayfasi.html', methods=['GET', 'POST'])
def giris_sayfasi():
    if current_user.is_authenticated:
        return redirect(url_for('anasayfa_kullanici')) 

    if request.method == 'POST':
        kullanici_adi = request.form['kullanici_adi']
        sifre = request.form['sifre']
        kullanici = Kullanici.query.filter_by(kullanici_adi=kullanici_adi).first()

        if kullanici and check_password_hash(kullanici.sifre, sifre):
            login_user(kullanici)
            return redirect(url_for('anasayfa_kullanici'))
        else:
            flash('Kullanıcı adı veya şifre hatalı!', 'hata')

    return render_template("giris_sayfasi.html")

@app.route('/cikis_ekrani.html')
@login_required
def cikis_ekrani():
    logout_user()
    flash('Başarıyla çıkış yaptınız.', 'basarili')
    return redirect(url_for('index'))

@app.route('/ogrenciler.html')
@login_required
def anasayfa_kullanici():
    ogrenciler = Ogrenci.query.filter_by(ekleyen_kullanici=current_user).order_by(Ogrenci.id.desc()).all()
    return render_template("ogrenciler.html", kullanici=current_user, ogrenciler=ogrenciler)

@app.route('/profil_ayarlari', methods=['GET', 'POST'])
@login_required
def profil_ayarlari():
    if request.method == 'POST':
        yeni_mesaj = request.form.get('kisisel_mesaj')
        current_user.kisisel_mesaj = yeni_mesaj
        db.session.commit()
        flash('Kişisel mesajınız güncellendi!', 'basarili')
        return redirect(url_for('anasayfa_kullanici'))

    return render_template('profil_ayarlari.html', kullanici=current_user)

@app.route('/ogrenci_ekle', methods=['GET', 'POST'])
@login_required
def ogrenci_ekle():
    if request.method == 'POST':
        ad = request.form['ad']
        soyad = request.form['soyad']
        numara = request.form['numara']
        sinif = request.form.get('sinif')
        dogum_tarihi = request.form.get('dogum_tarihi')

        if Ogrenci.query.filter_by(numara=numara).first():
            flash('Bu öğrenci numarası zaten sistemde kayıtlı!', 'hata')
            return redirect(url_for('ogrenci_ekle'))

        yeni_ogrenci = Ogrenci(
            ad=ad,
            soyad=soyad,
            numara=numara,
            sinif=sinif,
            dogum_tarihi=dogum_tarihi,
            ekleyen_kullanici=current_user
        )
        db.session.add(yeni_ogrenci)
        db.session.commit()
        flash('Öğrenci başarıyla eklendi!', 'basarili')
        return redirect(url_for('anasayfa_kullanici'))

    return render_template('ogrenci_ekle.html')

@app.route('/ogrenci_duzenle/<int:ogrenci_id>', methods=['GET', 'POST'])
@login_required
def ogrenci_duzenle(ogrenci_id):
    ogrenci = Ogrenci.query.get_or_404(ogrenci_id)
    if ogrenci.ekleyen_kullanici != current_user:
        flash('Bu öğrenciyi düzenlemeye yetkiniz yok!', 'hata')
        return redirect(url_for('anasayfa_kullanici'))

    if request.method == 'POST':
        ogrenci.ad = request.form['ad']
        ogrenci.soyad = request.form['soyad']

        yeni_numara = request.form['numara']
        if yeni_numara != ogrenci.numara:
            if Ogrenci.query.filter_by(numara=yeni_numara).first():
                flash('Bu öğrenci numarası zaten sistemde kayıtlı!', 'hata')
                return redirect(url_for('ogrenci_duzenle', ogrenci_id=ogrenci.id))
        ogrenci.numara = yeni_numara

        ogrenci.sinif = request.form.get('sinif')
        ogrenci.dogum_tarihi = request.form.get('dogum_tarihi')

        db.session.commit()
        flash('Öğrenci bilgileri başarıyla güncellendi!', 'basarili')
        return redirect(url_for('anasayfa_kullanici'))

    return render_template('ogrenci_duzenle.html', ogrenci=ogrenci)

@app.route('/ogrenci_sil/<int:ogrenci_id>', methods=['POST'])
@login_required
def ogrenci_sil(ogrenci_id):
    ogrenci = Ogrenci.query.get_or_404(ogrenci_id)
    if ogrenci.ekleyen_kullanici != current_user:
        flash('Bu öğrenciyi silmeye yetkiniz yok!', 'hata')
        return redirect(url_for('anasayfa_kullanici'))

    db.session.delete(ogrenci)
    db.session.commit()
    flash('Öğrenci başarıyla silindi!', 'basarili')
    return redirect(url_for('anasayfa_kullanici'))


@app.route('/dersler.html')
@login_required
def dersler():
    ders_listesi = Ders.query.filter_by(ekleyen_kullanici=current_user).order_by(Ders.ders_adi).all()
    return render_template("dersler.html", ders_listesi=ders_listesi)

@app.route('/ders_ekle', methods=['GET', 'POST'])
@login_required
def ders_ekle():
    if request.method == 'POST':
        ders_kodu = request.form['ders_kodu'].upper()
        ders_adi = request.form['ders_adi']
        kredi = request.form['kredi']
        akts = request.form.get('akts')

        if Ders.query.filter_by(ders_kodu=ders_kodu).first():
            flash('Bu ders kodu zaten sistemde kayıtlı!', 'hata')
            return redirect(url_for('ders_ekle'))

        try:
            kredi = int(kredi)
            akts = int(akts) if akts else None
        except ValueError:
            flash('Kredi ve AKTS sayısal değerler olmalıdır!', 'hata')
            return redirect(url_for('ders_ekle'))

        yeni_ders = Ders(
            ders_kodu=ders_kodu,
            ders_adi=ders_adi,
            kredi=kredi,
            akts=akts,
            ekleyen_kullanici=current_user
        )
        db.session.add(yeni_ders)
        db.session.commit()
        flash('Ders başarıyla eklendi!', 'basarili')
        return redirect(url_for('dersler'))

    return render_template('ders_ekle.html')

@app.route('/ders_duzenle/<int:ders_id>', methods=['GET', 'POST'])
@login_required
def ders_duzenle(ders_id):
    ders = Ders.query.get_or_404(ders_id)
    if ders.ekleyen_kullanici != current_user:
        flash('Bu dersi düzenlemeye yetkiniz yok!', 'hata')
        return redirect(url_for('dersler'))

    if request.method == 'POST':
        yeni_ders_kodu = request.form['ders_kodu'].upper()

        if yeni_ders_kodu != ders.ders_kodu:
            if Ders.query.filter_by(ders_kodu=yeni_ders_kodu).first():
                flash('Bu ders kodu zaten sistemde kayıtlı!', 'hata')
                return redirect(url_for('ders_duzenle', ders_id=ders.id))

        ders.ders_kodu = yeni_ders_kodu
        ders.ders_adi = request.form['ders_adi']

        try:
            ders.kredi = int(request.form['kredi'])
            ders.akts = int(request.form['akts']) if request.form['akts'] else None
        except ValueError:
            flash('Kredi ve AKTS sayısal değerler olmalıdır!', 'hata')
            return redirect(url_for('ders_duzenle', ders_id=ders.id))

        db.session.commit()
        flash('Ders bilgileri başarıyla güncellendi!', 'basarili')
        return redirect(url_for('dersler'))

    return render_template('ders_duzenle.html', ders=ders)

@app.route('/ders_sil/<int:ders_id>', methods=['POST'])
@login_required
def ders_sil(ders_id):
    ders = Ders.query.get_or_404(ders_id)
    if ders.ekleyen_kullanici != current_user:
        flash('Bu dersi silmeye yetkiniz yok!', 'hata')
        return redirect(url_for('dersler'))

    db.session.delete(ders)
    db.session.commit()
    flash('Ders başarıyla silindi!', 'basarili')
    return redirect(url_for('dersler'))



@app.route('/notlar.html')
@login_required
def notlar():
    tum_notlar = Not.query.filter_by(ekleyen_kullanici=current_user).order_by(Not.id.desc()).all()
    return render_template("notlar.html", tum_notlar=tum_notlar)


@app.route('/not_ekle/<int:ogrenci_id>', methods=['GET', 'POST'])
@login_required
def not_ekle(ogrenci_id):
    ogrenci = Ogrenci.query.get_or_404(ogrenci_id)

    if ogrenci.ekleyen_kullanici != current_user:
        flash('Bu öğrenciye not eklemeye yetkiniz yok!', 'hata')
        return redirect(url_for('anasayfa_kullanici'))

    kullanici_dersleri = Ders.query.filter_by(ekleyen_kullanici=current_user).order_by(Ders.ders_adi).all()

    if request.method == 'POST':
        ders_id = request.form['ders_id']
        not_degeri = request.form['not_degeri']

        secilen_ders = Ders.query.get(ders_id)
        if not secilen_ders or secilen_ders.ekleyen_kullanici != current_user:
            flash('Geçersiz ders seçimi!', 'hata')
            return redirect(url_for('not_ekle', ogrenci_id=ogrenci.id))

        try:
            not_degeri = int(not_degeri)
            if not (0 <= not_degeri <= 100):
                flash('Not değeri 0 ile 100 arasında olmalıdır!', 'hata')
                return redirect(url_for('not_ekle', ogrenci_id=ogrenci.id))
        except ValueError:
            flash('Not değeri sayısal olmalıdır!', 'hata')
            return redirect(url_for('not_ekle', ogrenci_id=ogrenci.id))

        mevcut_not = Not.query.filter_by(
            ogrenci_id=ogrenci.id,
            ders_id=secilen_ders.id,
            ekleyen_kullanici=current_user
        ).first()

        if mevcut_not:
            mevcut_not.not_degeri = not_degeri
            flash('Bu ders için öğrencinin notu güncellendi!', 'bilgi')
        else:
            yeni_not = Not(
                ogrenci_id=ogrenci.id,
                ders_id=secilen_ders.id,
                not_degeri=not_degeri,
                ekleyen_kullanici=current_user
            )
            db.session.add(yeni_not)
            flash('Not başarıyla eklendi!', 'basarili')

        db.session.commit()
        return redirect(url_for('ogrenci_detay', ogrenci_id=ogrenci.id))

    return render_template('not_ekle.html', ogrenci=ogrenci, dersler=kullanici_dersleri)


@app.route('/not_duzenle/<int:not_id>', methods=['GET', 'POST'])
@login_required
def not_duzenle(not_id):
    not_objesi = Not.query.get_or_404(not_id)

    if not_objesi.ekleyen_kullanici != current_user:
        flash('Bu notu düzenlemeye yetkiniz yok!', 'hata')
        return redirect(url_for('notlar'))

    ogrenci = not_objesi.ogrenci_bilgi 
    ders = not_objesi.ders_bilgi     

    if request.method == 'POST':
        yeni_not_degeri = request.form['not_degeri']

        try:
            yeni_not_degeri = int(yeni_not_degeri)
            if not (0 <= yeni_not_degeri <= 100):
                flash('Not değeri 0 ile 100 arasında olmalıdır!', 'hata')
                return redirect(url_for('not_duzenle', not_id=not_objesi.id))
        except ValueError:
            flash('Not değeri sayısal olmalıdır!', 'hata')
            return redirect(url_for('not_duzenle', not_id=not_objesi.id))

        not_objesi.not_degeri = yeni_not_degeri
        db.session.commit()
        flash('Not başarıyla güncellendi!', 'basarili')
        return redirect(url_for('ogrenci_detay', ogrenci_id=ogrenci.id))

    return render_template('not_duzenle.html', not_objesi=not_objesi, ogrenci=ogrenci, ders=ders)


@app.route('/not_sil/<int:not_id>', methods=['POST'])
@login_required
def not_sil(not_id):
    not_objesi = Not.query.get_or_404(not_id)
    ogrenci_id = not_objesi.ogrenci_bilgi.id 

    if not_objesi.ekleyen_kullanici != current_user:
        flash('Bu notu silmeye yetkiniz yok!', 'hata')
        return redirect(url_for('notlar'))

    db.session.delete(not_objesi)
    db.session.commit()
    flash('Not başarıyla silindi!', 'basarili')
    return redirect(url_for('ogrenci_detay', ogrenci_id=ogrenci_id))


@app.route('/ogrenci_detay/<int:ogrenci_id>')
@login_required
def ogrenci_detay(ogrenci_id):
    ogrenci = Ogrenci.query.get_or_404(ogrenci_id)

    if ogrenci.ekleyen_kullanici != current_user:
        flash('Bu öğrencinin detaylarını görüntülemeye yetkiniz yok!', 'hata')
        return redirect(url_for('anasayfa_kullanici'))


    ogrenci_notlari = Not.query.filter_by(ogrenci_bilgi=ogrenci, ekleyen_kullanici=current_user).order_by(Not.ders_id).all() # Burayı değiştirdik

    return render_template('ogrenci_detay.html', ogrenci=ogrenci, ogrenci_notlari=ogrenci_notlari)



@app.route('/raporlar.html')
@login_required
def raporlar():
    return render_template('/raporlar.html')

with app.app_context():
    db.create_all()

#if __name__ == "__main__":
    # app.run(debug=True)

import os
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))

