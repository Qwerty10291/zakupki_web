from logging import error
from flask import Blueprint, request, redirect, abort, session
from flask.templating import render_template
from controller import ParserController
import db_additions
from datetime import datetime, timedelta
from utils import sort_parameters, login_decorator

blueprint = Blueprint('create_and_show_requests',
                      __name__, template_folder='templates')
controller = ParserController()

@blueprint.route('/create_request', methods=['POST'])
@login_decorator
def create_request():
    user = db_additions.get_user(int(session['user']))
    parameters = {}
    if request.form.get('tag'):
        parameters['searchString'] = request.form['tag']
    min_price = request.form.get('min-price')
    max_price = request.form.get('max-price')

    if min_price:
        try:
            min_price = int(min_price)
            parameters['priceFromGeneral'] = str(min_price)
        except ValueError:
            return render_template('index.html', user=user, error='Неверный формат минимальной цены')
    if max_price:
        try:
            max_price = int(max_price)
            parameters['priceToGeneral'] = str(max_price)
        except ValueError:
            return render_template('index.html', user=user, error='Неверный формат максимальной цены')

    if min_price and max_price and min_price > max_price:
        return render_template('index.html', user=user, error='Минимальная цена не может быть больше максимальной')

    date_from = request.form.get('date-from')
    date_to = request.form.get('date-to')

    if date_from:
        try:
            datetime_from = datetime.strptime(date_from, '%d.%m.%Y')
            if datetime_from > datetime.now():
                return render_template('index.html', user=user, error='дата начала не может быть позже текущей даты')
            parameters['publishDateFrom'] = date_from
        except ValueError:
            return render_template('index.html', user=user, error='Неверный формат даты начала закупки')

    if date_to:
        try:
            datetime_to = datetime.strptime(date_to, '%d.%m.%Y')
            if datetime_to > datetime.now():
                return render_template('index.html', user=user, error='дата окончания не может быть позже текущей даты')
            parameters['publishDateTo'] = date_to
        except ValueError:
            return render_template('index.html', user=user, error='Неверный формат даты конца закупки')

    if not date_to and not date_from:
        datetime_to = datetime.now()
        date_to = datetime_to.strftime('%d.%m.%Y')

    if date_to and date_from:
        if datetime_from > datetime_to:
            return render_template('index.html', user=user, error='Дата начала не может быть позже даты конца')
        if datetime_to - datetime_from > timedelta(365):
            return render_template('index.html', user=user, error='Разница в датах может быть не более года')

    if date_from and not date_to:
        if datetime.now() - datetime_from < timedelta(365):
            parameters['publishDateTo'] = datetime.now().strftime('%d.%m.%Y')
        else:
            datetime_to = datetime_from + timedelta(365)
            parameters['publishDateTo'] = datetime_to.strftime('%d.%m.%Y')

    if date_to and not date_from:
        datetime_from = datetime_to - timedelta(365)
        parameters['publishDateFrom'] = datetime_from.strftime('%d.%m.%Y')

    search_filter = request.form.get('search-filter')
    if not search_filter:
        return abort(404)
    if search_filter not in sort_parameters:
        return abort(404)
    parameters['search-filter'] = sort_parameters[search_filter][0]
    parameters['sortBy'] = sort_parameters[search_filter][1]
    
    sort_direction = request.form.get('sort-direction')
    if not sort_direction:
        return abort(404)
    
    if sort_direction == 'from-new':
        parameters['sortDirection'] = 'false'
    elif sort_direction == 'from-old':
        parameters['sortDirection'] = 'true'
    else:
        return abort(404)
    controller.add_parser(int(session['user']), parameters)
    return redirect('/')
