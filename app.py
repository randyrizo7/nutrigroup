

from flask import Flask, render_template, request, flash, redirect, session, g, abort
from flask_debugtoolbar import DebugToolbarExtension
from sqlalchemy.exc import IntegrityError

from forms import UserAddForm, UserEditForm, LoginForm, PostForm, CreateGroupForm
from models import db, connect_db, User, Group, Post, Follows, Favorite 

import requests, email_validator

CURR_USER_KEY = "curr_user"

app = Flask(__name__)

app.config['SQLALCHEMY_DATABASE_URI'] = 'postgres:///nutrigroup'


app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SQLALCHEMY_ECHO'] = False
app.config['DEBUG_TB_INTERCEPT_REDIRECTS'] = True
app.config['SECRET_KEY'] = "Secret123"

toolbar = DebugToolbarExtension(app)

connect_db(app)

KEY = "25e20deb25e947dd8192d0d89ccbea7d"

BASE_URL = "https://api.spoonacular.com/"

find_random_joke = "food/jokes/random"
find_recipe = "recipes/findByIngredients"
find_random_recipe = "recipes/random"

key = {"apiKey" : KEY}


#####################################
#User sign up, log in and log out functions and routes. 

@app.before_request
def add_user_to_g():
    """If we're logged in, add curr user to Flask global."""

    if CURR_USER_KEY in session:
        g.user = User.query.get(session[CURR_USER_KEY])

    else:
        g.user = None


def do_login(user):
    """Log in user."""

    session[CURR_USER_KEY] = user.id


def do_logout():
    """Logout user."""

    if CURR_USER_KEY in session:
        del session[CURR_USER_KEY]

@app.route('/signup', methods=["GET", "POST"])
def signup():
    """Handle user signup.

    Create new user and add to DB. Redirect to home page.

    If form not valid, present form.

    If the there already is a user with that username: flash message
    and re-present form.
    """
    if CURR_USER_KEY in session:
        del session[CURR_USER_KEY]
    form = UserAddForm()

    if form.validate_on_submit():
        try:
            user = User.register(
                first_name = form.first_name.data,
                last_name=form.last_name.data,
                username=form.username.data,
                password=form.password.data,
                email=form.email.data,
                
            )
            db.session.commit()

        except IntegrityError as e:
            flash("Username already taken", 'danger')
            return render_template('signup.html', form=form)

        do_login(user)

        return redirect("/")

    else:
        return render_template('signup.html', form=form)

@app.route('/login', methods=["GET", "POST"])
def login():
    """Handle user login."""

    form = LoginForm()

    if form.validate_on_submit():
        user = User.authenticate(form.username.data,
                                 form.password.data)

        if user:
            do_login(user)
            flash(f"Hello, {user.username}!", "success")
            return redirect("/")

        flash("Invalid credentials.", 'danger')

    return render_template('login.html', form=form)


@app.route('/logout')
def logout():
    """Handle logout of user."""

    do_logout()

    flash("You have successfully logged out.", 'success')
    return redirect("/login")


# User Routes 

@app.route('/user/<int:user_id>')
def user_profile(user_id):
  """Show user profile"""

  #list all groups created by this user. 

  user = User.query.get_or_404(user_id)
  groups = (Group.query.filter(Group.creator_id == user_id).all())

  #list all favortited meals by this user. 

  favorites = (Favorite.query.filter(Favorite.user_id == user_id).all())

  return render_template('/profile.html', user=user, groups=groups, favorites=favorites)

@app.route('/user/<int:user_id>/following')
def show_following_groups(user_id):
  """ Show list of groups this user is following """

  if not g.user:
    flash("ACCESS unauthorized.", "danger")
    return redirect("/")

  user = User.query.get_or_404(user_id)
  return render_template('/following.html', user=user)

@app.route('/group/<int:group_id>/followers')
def show_group_followers(group_id):
  """Show list of users following a group"""

  if not g.user:
    flash("Access unauthorized.", "danger")
    return redirect('/')

  group = Group.query.get_or_404(group_id)
  return render_template('followers.html', group=group)

@app.route('/user/follow/<int:follow_id>', methods=['POST'])
def add_follow(follow_id):
    """Add a follow to the group from the currently-logged-in user."""

    if not g.user:
        flash("Access unauthorized.", "danger")
        return redirect("/")

    followed_group = Group.query.get_or_404(follow_id)
    g.user.following.append(followed_group)
    db.session.commit()

    return redirect(f"/user/{g.user.id}/following")

@app.route('/group/stop-following/<int:follow_id>', methods=['POST'])
def stop_following(follow_id):
    """Have currently-logged-in-user stop following this group."""

    if not g.user:
        flash("Access unauthorized.", "danger")
        return redirect("/")

    followed_group = Group.query.get(follow_id)
    g.user.following.remove(followed_group)
    db.session.commit()

    return redirect(f"/user/{g.user.id}/following")

@app.route('/users/profile', methods=["GET", "POST"])
def edit_user_profile():
    """Edit a user profile"""

    if not g.user:
        flash("ACCESS unauthorized", "danger")
        return redirect("/")

    user = g.user
    form = UserEditForm(obj=user)

    if form.validate_on_submit():
        if User.authenticate(user.username, form.password.data):
            user.username = form.username.data
            user.email = form.email.data
            user.bio = form.bio.data
            user.first_name = form.first_name.data
            user.last_name = form.last_name.data

            db.session.commit()
            return redirect(f"/users/{user.id}")

        flash("Wrong password, please try again.", 'danger')

    return render_template('edit.html', form=form, user_id=user.id)


# Group routes 

@app.route('/group/new', methods=["GET", "POST"])
def create_group():
    """Create a group """

    if not g.user:
        flash("Access unauthorized", "danger")
        return redirect("/")

    form = CreateGroupForm()

    if form.validate_on_submit():
        group = Group(title=form.title.data, description=form.description.data)
        g.user.groups.append(group)
        db.session.commit()

        return redirect(f"/user/{g.user.id}")
    
    return render_template('newgroup.html', form=form)

@app.route('/group/<int:group_id>', methods=["GET"])
def show_group(group_id):
    """Show Group and posts"""

    group = Group.query.get_or_404(group_id)
    post= (Post
            .query
            .filter(Post.group_id == group_id)
            .order_by(Post.timestamp.desc())
            .limit(100)
            .all())

    return render_template('showgroup.html', group=group, post=post)

@app.route('/group/<int:group_id>/followers')
def users_followers(group_id):
    """Show list of followers of this group."""

    if not g.user:
        flash("Access unauthorized.", "danger")
        return redirect("/")

    group = Group.query.get_or_404(group_id)
    return render_template('followers.html', group=group)


@app.route('/group/<int:group_id>/delete', methods=["POST"])
def delete_group(group_id):
    """Delete a group"""

    if not g.user:
        flash("ACCESS unauthorized", "danger")
    
    group = Group.query.get_or_404(group_id)
    if group.creator_id != g.user.id:
        flash("ACCESS unauthorized", "danger")
        return redirect("/")

    db.session.delete(group)
    db.session.commit()

    return redirect(f"/users/{g.user.id}")




#POST routes 

@app.route('/group/<int:group_id>/post/new', methods=["GET", "POST"])
def posts_add(group_id):
    """Add a post to a group:

    Show form if GET. If valid, update message and redirect to user page.
    """

    if not g.user:
        flash("Access unauthorized.", "danger")
        return redirect("/")

    form = PostForm()
    

    if form.validate_on_submit():
        group = Group.query.get(group_id)
        groupid = group.id
        post = Post(title= form.title.data, text=form.text.data, group_id=groupid)
        #db.session.add(post)
        g.user.post.append(post)
        #db.session.add(group)
        #group.post.append(post)
        
        #group.post.append(post)
        #g.user.groups.append(post)
        #group.post.append(group)
        #post.group.append(group)
        #db.session.add(group)
        #db.session.add(post)
        db.session.commit()

        return redirect(f"/group/{group.id}")

    return render_template('newpost.html', form=form)




@app.route('/')
def home_page():
    joke_response = str(requests.request("GET", BASE_URL + find_random_joke, params=key).json()['text'])
    return render_template('home.html', joke=joke_response)


@app.route('/recipes')
def get_recipes():
  if (str(request.args['ingridients']).strip() != ""):
      # If there is a list of ingridients -> list
      querystring = {"number":"20","ranking":"1","ignorePantry":"false","ingredients":request.args['ingridients']}
      response = requests.request("GET", BASE_URL + find_recipe, params={**querystring, **key}).json()
      return render_template('recipes.html', recipes=response)
  else:
      # Random recipes
      querystring = {"number":"20"}
      response = requests.request("GET", BASE_URL + find_random_recipe, params={**querystring, **key}).json()
      print(response)
      return render_template('recipes.html', recipes=response['recipes'])


@app.route('/recipe', methods=["GET", "POST"])
def get_recipe():
    
    if not g.user:
        flash("Access unauthorized.", "danger")
        return redirect("/")

    recipe_id = request.args['id']
    recipe_info_endpoint = "recipes/{0}/information".format(recipe_id)
    ingedientsWidget = "recipes/{0}/ingredientWidget".format(recipe_id)
    equipmentWidget = "recipes/{0}/equipmentWidget".format(recipe_id)
    nutritionWidget = "recipes/{0}/nutritionWidget".format(recipe_id)

    recipe_info = requests.request("GET", BASE_URL + recipe_info_endpoint, params=key).json()
    recipe_headers = {'Accept': "text/html"}
 
    querystring = {"defaultCss":"true", "showBacklink":"false"}

    recipe_info['inregdientsWidget'] = requests.request("GET", BASE_URL + ingedientsWidget, headers=recipe_headers, params={**querystring, **key}).text
    recipe_info['equipmentWidget'] = requests.request("GET", BASE_URL + equipmentWidget, headers=recipe_headers, params={**querystring, **key}).text
    recipe_info['nutritionWidget'] = requests.request("GET", BASE_URL + nutritionWidget, headers=recipe_headers, params={**querystring, **key}).text  
 

    favorite = Favorite(meal_id=recipe_id)

    g.user.favorite.append(favorite)
        

    db.session.commit()

        
    return render_template('recipe.html', recipe=recipe_info)

if __name__ == '__main__':
  app.run()