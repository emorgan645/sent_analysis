{% extends 'base.html' %}
{% import 'bootstrap/wtf.html' as wtf %}
    <!DOCTYPE html>
    <html>

    <head>
        <title>Login</title>
    </head>

    {% block app_content %}
    <body class="text-center">
        <div class="container">
            <h1>Sign In</h1>
            <div class="row" style="padding-left: 42%;">
                <div class="col-md-4">
                    {{ wtf.quick_form(form) }}
                </div>
            </div>
            <p>New User? <a href="{{ url_for('register') }}">Click to Register!</a></p>
        </div>
    </div>
        {% endblock %}
    </body>