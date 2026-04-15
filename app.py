import os
import re
from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
import openai
import moyasar

app = Flask(__name__)
app.config['SECRET_KEY'] = 'pixel-secret-123' 
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(os.path.abspath(os.path.dirname(__file__)), 'database.db')
db = SQLAlchemy(app)

# إعداد Moyasar
openai.api_key = os.getenv("OPENAI_API_KEY")
moyasar.api_key = os.getenv("MOYASAR_API_KEY")


# --- قاعدة بيانات المستخدمين ---
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    password = db.Column(db.String(100), nullable=False)
    credits = db.Column(db.Integer, default=3)

with app.app_context():
    db.create_all()

# --- إعداد نظام الدخول ---
login_manager = LoginManager()
login_manager.login_view = 'login'
login_manager.init_app(app)

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# --- المسارات (Routes) ---

@app.route('/')
@login_required
def home():
    return render_template('index.html', user=current_user)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        user = User.query.filter_by(username=username).first()
        if user and user.password == password:
            login_user(user)
            return redirect(url_for('home'))
        return "❌ خطأ في الاسم أو كلمة السر"
    return render_template('login.html')

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        password_criteria = r"^(?=.*[a-z])(?=.*[A-Z])(?=.*\d).{8,}$"
        
        if not re.match(password_criteria, password):
            return "❌ كلمة السر ضعيفة! يجب أن تحتوي على 8 خانات، حرف كبير، حرف صغير، ورقم."

        if User.query.filter_by(username=username).first():
            return "❌ اسم المستخدم هذا محجوز لـ لاعب آخر!"
            
        new_user = User(username=username, password=password)
        db.session.add(new_user)
        db.session.commit()
        return redirect(url_for('login'))
    return render_template('signup.html')
    
@app.route('/generate', methods=['POST'])
@login_required
def generate():
if current_user.credits <= 0:
return jsonify({"text": "❌ انتهت نقاطك المجانية! يرجى شراء باقة جديدة."})

user_data = request.json.get('prompt')
try:
response = openai.ChatCompletion.create(
model="gpt-4o-mini", # تم التحديث لنموذج أحدث وأفضل للمقالات الطويلة
messages=[
{
"role": "system",
"content": (
"أنت كاتب محترف وخبير في كتابة المقالات الطويلة (Long-form content). "
"يجب أن يكون المقال مفصلاً جداً، غنياً بالمعلومات، ويحتوي على مقدمة، "
"عناوين فرعية جذابة، فقرات شرح عميقة، وخاتمة. "
"استهدف كتابة ما يقارب 1500 كلمة."
)
},
{"role": "user", "content": f"اكتب مقالاً شاملاً ومفصلاً عن: {user_data}"}
],
max_tokens=3000, # رفع الحد للسماح بكتابة مقال طويل (الـ 1500 كلمة تساوي تقريباً 2000-2500 توكن)
temperature=0.7 # درجة إبداع مناسبة لكتابة المقالات
)

current_user.credits -= 1
db.session.commit()

return jsonify({
"text": response.choices[0].message.content,
"new_credits": current_user.credits
})
except Exception as e:
return jsonify({"text": f"خطأ: {str(e)}"})



@app.route('/plans')
@login_required
def plans():
    return render_template('plans.html')

@app.route('/checkout/<int:amount>')
@login_required
def checkout(amount):
    return render_template('payment.html', amount=amount*100)

@app.route('/success')
@login_required
def success():
    status = request.args.get('status')
    if status == 'paid':
        # تحديث النقاط: مثلاً كل ريال بنقطتين
        current_user.credits += 20 
        db.session.commit()
        return "<h1>✅ تم الدفع بنجاح! تم إضافة النقاط لرصيدك.</h1><a href='/'>العودة للمنضدة</a>"
    return "<h1>❌ فشلت عملية الدفع</h1><a href='/plans'>حاول مرة أخرى</a>"

@app.route('/admin_panel')
@login_required
def admin_panel():
    if current_user.username != 'admin':
        return "❌ غير مسموح لك بالدخول"
    users = User.query.all() 
    return render_template('admin.html', users=users)

@app.route('/logout')
def logout():
    logout_user()
    return redirect(url_for('login'))

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))
