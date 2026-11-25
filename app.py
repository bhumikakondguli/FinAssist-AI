from flask import Flask, render_template, request, redirect, url_for, jsonify, flash, send_file
import sqlite3, os, csv, io, json
from datetime import datetime, date
from collections import defaultdict
from dotenv import load_dotenv

load_dotenv()
app = Flask(__name__)
app.secret_key = os.getenv('SECRET_KEY', 'finassist-demo-key-change-me')
DB = os.path.join(os.path.dirname(__file__), 'finassist.db')

CATEGORIES = ['Food','Transport','Shopping','Bills','Entertainment','Health','Education','Rent','Salary','Other']

def db():
    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    with db() as c:
        c.execute('''CREATE TABLE IF NOT EXISTS transactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT, date TEXT NOT NULL, description TEXT NOT NULL,
            amount REAL NOT NULL, type TEXT NOT NULL CHECK(type IN ('income','expense')), category TEXT NOT NULL)''')
        c.execute('''CREATE TABLE IF NOT EXISTS budgets (
            id INTEGER PRIMARY KEY AUTOINCREMENT, month TEXT NOT NULL, category TEXT NOT NULL, amount REAL NOT NULL,
            UNIQUE(month, category))''')

def categorize(description, typ):
    if typ == 'income': return 'Salary' if any(x in description.lower() for x in ['salary','pay','stipend']) else 'Other'
    d = description.lower()
    rules = {'Food':['food','restaurant','cafe','coffee','grocery','groceries','swiggy','zomato'],
             'Transport':['bus','metro','cab','uber','ola','fuel','petrol'], 'Shopping':['shop','shopping','amazon','flipkart','clothes'],
             'Bills':['bill','electric','water','internet','recharge'], 'Entertainment':['movie','cinema','netflix','game'],
             'Health':['doctor','medical','medicine','pharmacy'], 'Education':['college','course','book','tuition'], 'Rent':['rent']}
    for category, words in rules.items():
        if any(w in d for w in words): return category
    return 'Other'

def get_data(month=None):
    with db() as c:
        rows = c.execute('SELECT * FROM transactions ORDER BY date DESC, id DESC').fetchall()
        budgets = c.execute('SELECT * FROM budgets ORDER BY month DESC, category').fetchall()
    tx = [dict(r) for r in rows if not month or r['date'][:7] == month]
    income = sum(r['amount'] for r in tx if r['type']=='income')
    expenses = sum(r['amount'] for r in tx if r['type']=='expense')
    categories = defaultdict(float)
    for r in tx:
        if r['type']=='expense': categories[r['category']] += r['amount']
    return tx, income, expenses, dict(categories), [dict(b) for b in budgets]

@app.route('/')
def dashboard():
    month = request.args.get('month', date.today().strftime('%Y-%m'))
    tx, income, expenses, categories, budgets = get_data(month)
    month_budgets = [b for b in budgets if b['month']==month]
    budget_view = []
    for b in month_budgets:
        spent = categories.get(b['category'],0)
        budget_view.append({**b, 'spent':spent, 'remaining':b['amount']-spent, 'percent':min(100, round(spent/b['amount']*100,1)) if b['amount'] else 0})
    return render_template('index.html', month=month, tx=tx, income=income, expenses=expenses, balance=income-expenses,
                          categories=categories, budget_view=budget_view, category_list=CATEGORIES)

@app.route('/transactions/add', methods=['POST'])
def add_transaction():
    try:
        dt=request.form.get('date') or date.today().isoformat(); desc=request.form.get('description','').strip()
        amount=float(request.form.get('amount','0')); typ=request.form.get('type','expense')
        category=request.form.get('category') or categorize(desc,typ)
        if not desc or amount<=0 or typ not in ('income','expense'): raise ValueError('Please enter a description and a positive amount.')
        with db() as c: c.execute('INSERT INTO transactions(date,description,amount,type,category) VALUES(?,?,?,?,?)',(dt,desc,amount,typ,category))
        flash('Transaction added.','success')
    except Exception as e: flash(str(e) or 'Unable to add transaction.','danger')
    return redirect(url_for('dashboard', month=(request.form.get('date') or date.today().isoformat())[:7]))

@app.route('/transactions/<int:tid>/delete', methods=['POST'])
def delete_transaction(tid):
    with db() as c: c.execute('DELETE FROM transactions WHERE id=?',(tid,))
    flash('Transaction deleted.','success'); return redirect(url_for('dashboard'))

@app.route('/budgets/add', methods=['POST'])
def add_budget():
    try:
        month=request.form['month']; category=request.form['category']; amount=float(request.form['amount'])
        if amount<=0: raise ValueError('Budget amount must be positive.')
        with db() as c: c.execute('INSERT INTO budgets(month,category,amount) VALUES(?,?,?) ON CONFLICT(month,category) DO UPDATE SET amount=excluded.amount',(month,category,amount))
        flash('Budget saved.','success')
    except Exception as e: flash(str(e) or 'Unable to save budget.','danger')
    return redirect(url_for('dashboard', month=request.form.get('month',date.today().strftime('%Y-%m'))))

@app.route('/import', methods=['POST'])
def import_csv():
    file=request.files.get('file')
    if not file or not file.filename.lower().endswith('.csv'): flash('Choose a CSV file.','danger'); return redirect(url_for('dashboard'))
    try:
        stream=io.StringIO(file.stream.read().decode('utf-8-sig')); reader=csv.DictReader(stream)
        required={'date','description','amount','type'}
        if not reader.fieldnames or not required.issubset(set(x.strip().lower() for x in reader.fieldnames)): raise ValueError('CSV needs columns: date, description, amount, type (category optional).')
        added=0
        for row in reader:
            row={k.strip().lower():v.strip() for k,v in row.items() if k}
            dt=datetime.strptime(row['date'], '%Y-%m-%d').date().isoformat(); desc=row['description']; amount=float(row['amount']); typ=row['type'].lower()
            if not desc or amount<=0 or typ not in ('income','expense'): continue
            cat=row.get('category') or categorize(desc,typ)
            with db() as c: c.execute('INSERT INTO transactions(date,description,amount,type,category) VALUES(?,?,?,?,?)',(dt,desc,amount,typ,cat))
            added+=1
        flash(f'Imported {added} transaction(s).','success')
    except Exception as e: flash(f'Import failed: {e}','danger')
    return redirect(url_for('dashboard'))

@app.route('/export')
def export_csv():
    month=request.args.get('month')
    tx, *_=get_data(month)
    out=io.StringIO(); w=csv.writer(out); w.writerow(['date','description','amount','type','category'])
    for r in tx: w.writerow([r['date'],r['description'],r['amount'],r['type'],r['category']])
    mem=io.BytesIO(out.getvalue().encode('utf-8')); mem.seek(0)
    return send_file(mem, mimetype='text/csv', as_attachment=True, download_name=f'finassist_{month or "all"}.csv')

@app.route('/api/chart-data')
def chart_data():
    month=request.args.get('month',date.today().strftime('%Y-%m')); _,income,expenses,cats,_=get_data(month)
    return jsonify({'income':income,'expenses':expenses,'categories':cats})

@app.route('/assistant', methods=['POST'])
def assistant():
    question=request.json.get('question','').strip(); month=request.json.get('month',date.today().strftime('%Y-%m'))
    tx,income,expenses,cats,budgets=get_data(month)
    context={'month':month,'income':round(income,2),'expenses':round(expenses,2),'balance':round(income-expenses,2),'categories':cats}
    answer=None
    api_key=os.getenv('OPENAI_API_KEY')
    if api_key:
        try:
            from openai import OpenAI
            client=OpenAI(api_key=api_key)
            res=client.chat.completions.create(model=os.getenv('OPENAI_MODEL','gpt-4o-mini'),messages=[
                {'role':'system','content':'You are FinAssist AI, a budgeting explainer. Use only the supplied verified figures; do not invent numbers or offer investment, tax, credit, or regulated financial advice. Explain in simple language.'},
                {'role':'user','content':f'Financial summary: {json.dumps(context)}\nQuestion: {question}'}],temperature=0.2)
            answer=res.choices[0].message.content
        except Exception: answer=None
    if not answer:
        q=question.lower()
        if 'budget' in q:
            answer=f'For {month}, recorded expenses are ₹{expenses:,.2f}. Review your category budgets below the dashboard to compare planned limits with recorded spending.'
        elif 'save' in q or 'balance' in q:
            answer=f'For {month}, recorded income is ₹{income:,.2f} and expenses are ₹{expenses:,.2f}. The difference is ₹{income-expenses:,.2f}. This is based only on transactions entered into FinAssist AI.'
        elif cats:
            top=max(cats,key=cats.get); answer=f'For {month}, your recorded expenses total ₹{expenses:,.2f}. The largest expense category is {top} at ₹{cats[top]:,.2f}. Ask about a category, budget or monthly summary for more detail.'
        else: answer=f'I do not have recorded transactions for {month} yet. Add or import transactions first, then I can summarize the data. I can answer supported questions using recorded totals.'
        answer+=' (Rule-based fallback mode.)'
    return jsonify({'answer':answer,'mode':'AI' if api_key and answer else 'fallback','summary':context})

@app.route('/reports')
def reports():
    month=request.args.get('month',date.today().strftime('%Y-%m')); tx,income,expenses,cats,budgets=get_data(month)
    return render_template('reports.html',month=month,tx=tx,income=income,expenses=expenses,balance=income-expenses,categories=cats)

if __name__=='__main__':
    init_db(); app.run(debug=True)
