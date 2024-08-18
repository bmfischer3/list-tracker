
import awsgi
import os
import boto3
from boto3.dynamodb.conditions import Key

from flask import (
    Flask,
    request,
    render_template,
    redirect,
    url_for,
    session
)
import datetime
from pprint import pprint

app = Flask(__name__, template_folder='templates')

app.secret_key = 'secret key'
table_name = 'listtracker-api-lists'


import logging

logging.basicConfig()

aws_session = boto3.Session()

@app.route('/success', methods=['GET', 'POST'])
def return_success():
    return render_template('success.html')

@app.route('/', methods=['GET', 'POST'])
def home():
    return render_template('home.html')

@app.route('/add-list', methods=['GET', 'POST'])
def addlist():
    """Creates a new list provided the list_name. 

    Args:
        list_name (str): _description_

    Returns:
        _type_: _description_
    """
    logging.info("/add-list route successfuly reached.")

    if request.method == 'POST':
        try:
            logging.info('add-list route, post method successfully reached.')

            list_name = str(request.form.get('list_name'))
            user_id = str(request.form.get('user_id'))



            # Extract the list_name from the query parameters.

            logging.info(f'Form values successfully extracted.\nList_name is: {list_name} \nuser_id is: {user_id}')

            if is_valid_dynamodb_name(list_name) == True:
                logging.info(f'List name: {list_name}, has been validated.')

                try:
                    dynamodb = boto3.resource('dynamodb')
                    time = get_current_time()
                    table = dynamodb.Table(table_name)

                    list_id = str(user_id + '-' + list_name)
                        

                    insert_list_resp = table.put_item(
                        Item={
                            'user_id': user_id,
                            'list_id': list_id,
                            'list_name': list_name,
                            'created_datetime': time
                        },
                    )
                    pprint(insert_list_resp, indent=4)
                    return redirect(url_for('return_success'), 200)

                except Exception as e:
                    logging.info(f'An error occurred accessing or updating the dynamodb table: {table_name}.')
                    return redirect(url_for('return_error_page'), 400)

            else:
                logging.info(f'{list_name} is not a valid name to insert into dynamodb')
                return redirect(url_for('addlist'), 400)    
                      
        except Exception as e:
            logging.info(f'Error occured with capturing form submission details on /add-list route. \nException: {e}')
            redirect(url_for('return_error_page'), 400)

    else:
        return render_template('add-list.html')


@app.route('/add-item', methods=['GET', 'POST'])
def additem():

    logging.info("/add-item route and 'additem' function within the route successfully reached.")

    if request.method != 'POST':
        return render_template('add-item.html')

    if request.method == 'POST':
        user_id = request.form.get('user_id')
        list_id = request.form.get('list_id')

        if user_id:
            logging.info(f"Successful in getting user_id: {user_id}  from the form.")
            session['unique_lists'] = get_available_lists(user_id)
            return render_template('add-item.html')
        
        elif list_id:


            logging.info(f"Successful in getting list_id: {list_id}  from the form.")

            # Get items from submission form. 
            user_id = str(request.form.get('user_id2'))
            item_name = str(request.form.get('item_name'))
            item_qty = str(request.form.get('item_qty'))
            list_id = str(request.form.get('list_id'))

            logging.info(f"Successful in capturing user_id2, item_name, item_qty, and list_id from the form. \
                         Those values are: {user_id}, {item_name}, {item_qty}, and {list_id}")
        
        
            try:
                if add_item(user_id, list_id, item_name, item_qty) == True:
                    logging.info(f"add_item function returns true. Put_item function on dynamodb table is successful")
                    return render_template('add-item.html')
                
            except Exception as e:
                logging.info(f"An error occurred trying to use the Put_item function on the dynamodb table.")

                return redirect(url_for('additem'), 400)  
    else:
        logging.info(f"Post method for /add-item was reached, but a user_id and list_id were not provided. These are equal to: \
                        user_id: {user_id} and list_id: {list_id}")
        return redirect(url_for('additem'), 400) 



@app.route('/list-contents', methods=['GET','POST'])
def get_list_items():
    if request.method == 'POST':
        user_id = request.form.get('user_id')
        
        if user_id:
            lists = get_available_lists(user_id)
            requested_list_id = request.form.get('list_id')
            
            for dict in lists:
                if dict['list_id'] == requested_list_id:
                    pprint(dict, indent=4)


                    # Because the list item count will vary, we will create a new list of tuples to pass to the flask html page. 
                    session['requested_list_items'] = sorted(list(dict.items()))
                    pprint(session['requested_list_items'], indent=4)

                    return redirect(url_for('get_list_items')) 
                
            pprint(lists, indent=4)
            return render_template('get-lists.html')

    else:
        return render_template('get-lists.html')

@app.errorhandler(404)
def pageNotFound():
    return render_template('404.html'), 404

@app.route('/error', methods=['GET'])
def return_error_page():
    return render_template('error.html')


def get_available_lists(user_id:str) -> dict:
    """Retrieves the lists held by the user_id specified. 

    Args:
        user_id (str): user_id

    Returns:
        dict: dict
    """
    dynamodb = boto3.resource('dynamodb')
    table = dynamodb.Table(table_name)
    user_id = str(user_id)

    try:
        response = table.query(
            KeyConditionExpression=Key('user_id').eq(user_id)
        )
    except Exception as err:
        logging.error(
            f'Couldn\'t query for user_id == {user_id}, error response: {err}'
        )
        raise
    else:
        return response['Items']

def get_current_time() -> str:
    """Returns the exact current datetime as a string.

    Returns:
        str: Datetime in the format '2017-01-12T14:12:06+0000'.
    """
    tz = datetime.timezone.utc
    now = datetime.datetime.now(tz=tz)
    formatted_time = now.strftime("%Y-%m-%dT%H:%M:%S%z")
    return formatted_time

def is_valid_dynamodb_name(name: str) -> bool:
    """Check if the provided string meets DynamoDB naming rules.

    Args:
        name (str): The name to validate.

    Returns:
        bool: True if the name is valid, False otherwise.
    """
    if not (3 <= len(name) <= 255):
        return False
    
    allowed_characters = set("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_-.")

    for char in name:
        if char not in allowed_characters:
            return False
    
    return True



def add_item(user_id: str, list_id: str, item_name: str, item_qty: int) -> bool:    
    """Runs put_item call on the dynamodb table specified at top of index.py 

    Args:
        user_id (str): user_id
        list_id (str): list_id
        item_name (str): item_name
        item_qty (int): item_qty

    Returns:
        bool: True if operation is successful. False if error is encountered. 
    """
    ddb_client = aws_session.client('dynamodb')
    item_name_and_qty = str(item_name + '-' + item_qty)
    list_id = str(list_id)

    try:
        counter = 0
        item_name_count = str('item_' + str(counter))
        pprint('try hit on add_item')

        current_dict = get_item_attributes(user_id, list_id)
        pprint(current_dict, indent=4)

        while item_name_count in current_dict:
            # Should probably put some kind of stopper on this eventually. 
            counter += 1
            item_name_count = str('item_' + str(counter))
    
        if item_name_count:
            pprint(f'trying to add {item_name}')
            new_item_dict = {
                item_name_count : {'S': item_name_and_qty}
            }
            item_dict = current_dict

            item_dict.update(new_item_dict)

            ddb_client.put_item(
                TableName = table_name,
                Item=item_dict
            )
            pprint(f'successful in addin g{item_name}')
            return True
        
    except Exception as e:
        pprint(f'some error occurred: {e}')
        return False

def get_item_attributes(user_id: str, list_id: str) -> dict:
    """Retrieves all of the attributes for the specified user_id and list_id. 

    Args:
        user_id (str): user_id
        list_id (str): list_id

    Returns:
        dict: Returns a dict of the attributes with the user_id and list_id. Returns a blank list if there's an error. 
    """
    ddb_client = aws_session.client('dynamodb')
    try:
        item_attributes = ddb_client.get_item(
            TableName=table_name,
            Key={
                'user_id' : {'S' : str(user_id)},
                'list_id' : {'S' : str(list_id)}
            }
        )
        if 'Item' in item_attributes:
            return(item_attributes['Item'])
        else:
            pprint('Error in arguments or in finding the attributes.')
            return {}
    
    except Exception as e:
        pprint(f'Error retrieving item: str{e}')
        return {}




def handler(event, context):
    # list_name = event["queryStringParameters"]["list_name"]
    # path = event["queryStringParameters"]["path"]
    return awsgi.response(app, event, context)


# Not in lambda, run flask app. 
if not os.environ.get("AWS_LAMBDA_FUNCTION_NAME"):
    app.run('127.0.0.1', 8080, os.environ.get("APP_DEBUG") != "")

