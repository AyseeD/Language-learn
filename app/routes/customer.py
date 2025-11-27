from flask import Blueprint, render_template
from flask_login import login_required

customer = Blueprint('customer', __name__)


@login_required
@customer.route('/courses', methods=['GET'])
def courses():
    return render_template('courses.html')


@login_required
@customer.route('/kanji/draw', methods=['GET'])
def kanji():
    return render_template('draw.html')
