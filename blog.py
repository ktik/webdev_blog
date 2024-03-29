import webapp2
import jinja2
import os
import re
import random
import hmac
import string
import time
import json
from google.appengine.api import memcache
from google.appengine.ext import db

jinja_environment = jinja2.Environment(
    loader=jinja2.FileSystemLoader(os.path.dirname(__file__)), autoescape=True)

USER_RE = re.compile(r"^[a-zA-Z0-9_-]{3,20}$")
PASS_RE = re.compile(r"^.{3,20}$")
EMAIL_RE = re.compile(r"^[\S]+@[\S]+\.[\S]+$")

def make_pwd_hash(pwd, salt):
		hash_salt = hmac.new(salt, pwd).hexdigest()
		hash_salt += '|'
		hash_salt += salt
		return_str = ''.join(hash_salt)
		return return_str

def valid_username(username):
    return username and USER_RE.match(username)

def valid_password(pwd):
    return pwd and PASS_RE.match(pwd)

def valid_email(email):
    return not email or EMAIL_RE.match(email)

def load_front_page(update=False):
	posts = memcache.get('blog')
	if not update and posts:
		return posts
	else:
		posts = db.GqlQuery("SELECT * FROM Entry ORDER BY created DESC")
		posts = list(posts)
		memcache.set('blog', posts)
		memcache.set('time', time.time())
		return posts

def load_blog_post(post_id, update=False):
	post = memcache.get('post_'+post_id)
	if not update and post:
		return post
	else:
		post = Entry.get_by_id(int(post_id))
		#post = list(post)
		memcache.set('post_'+post_id, post)
		memcache.set('time_post_'+post_id, time.time())
		return post


class Entry(db.Model):
	entry_id = db.IntegerProperty()
	subject = db.StringProperty(required = True)
	content = db.TextProperty(required = True)
	created = db.DateTimeProperty(auto_now_add = True)

class UserAccount(db.Model):
	username = db.StringProperty(required = True)
	password = db.StringProperty(required = True)
	email = db.EmailProperty()

class Handler(webapp2.RequestHandler):
	def write(self, *a, **kw):
		self.response.out.write(*a, **kw)

	def render_str(self, template, **params):
		t = jinja_environment.get_template(template)
		return t.render(params)

	def render(self, template, **kw):
		self.write(self.render_str(template, **kw))

class NewPost(Handler):
	def render_newpost(self, subject="", content="", error=""):
		self.render("newpost.html", subject=subject, content=content, error=error)

	def get(self):
		self.render_newpost()

	def post(self):
		subject = self.request.get("subject")
		content = self.request.get("content")

		if subject and content:
			e = Entry(subject=subject, content=content)
			e.put()
			#post = db.GqlQuery("SELECT * FROM Entry WHERE ID=:1", )

			myID = str(e.key().id())
			load_front_page(True)
			self.redirect("/blog/%s" %myID)
			#self.write("thanks!")
		else:
			error = "We need a subject and an entry"
			self.render_newpost(subject, content, error)

class Blog(Handler):
	def get(self):
		posts = load_front_page(False)
		time_since = int(time.time() - memcache.get('time'))
		self.render("blog.html", posts=posts, time=time_since)

class BlogJson(Handler):
	def get(self):
		allposts = db.GqlQuery("SELECT * FROM Entry")
		postsjson = []
		for post in allposts:
			d={}
			d['subject'] = post.subject
			d['content'] = post.content
			d['created'] = 	post.created.strftime("%a %b %d %H:%M:%S %Y")
			postsjson.append(d)

		j = json.dumps(postsjson)
		self.response.headers['Content-Type'] = "application/json; charset=utf-8"
		self.response.out.write(j)

class PermalinkJson(Handler):
	def get(self, post_id):
		post = Entry.get_by_id(int(post_id))
		d={}
		d['subject'] = post.subject
		d['content'] = post.content
		d['created'] = 	post.created.strftime("%a %b %d %H:%M:%S %Y")
		j = json.dumps(d)
		self.response.headers['Content-Type'] = "application/json; charset=utf-8"
		self.response.out.write(j)


class PostHandler(Handler):
	def get(self, post_id):
		post = load_blog_post(post_id)
		time_since = int(time.time() - memcache.get('time_post_'+post_id))
		self.render("post.html", post=post, time=time_since)

class Signup(Handler):

	def render_signup(self, username="", email="", uerror="", perror="", eerror=""):
		self.render("signup.html", username=username, email=email, uerror=uerror, perror=perror, eerror=eerror)
	
	def get_salt(self):
		return ''.join(random.choice(string.ascii_letters) for x in range(5))

	def make_pwd_hash(self, pwd, salt):
		hash_salt = hmac.new(salt, pwd).hexdigest()
		hash_salt += '|'
		hash_salt += salt
		return_str = ''.join(hash_salt)
		return return_str

	def get(self):
		self.render_signup()

	def post(self):
		username = self.request.get("username")
		pwd = self.request.get("password")
		ver = self.request.get("verify")
		email = self.request.get("email")
		have_error = False
		params = dict(username=username,
			email=email)

		if not valid_username(username):
			params['uerror'] = "That's not a valid username"
			have_error = True

		if not valid_password(pwd):
			params['perror'] = "That's not a valid password"
			have_error = True
		elif pwd != ver:
			params['perror'] = "Your passwords did not match"
			have_error = True

		if not valid_email(email):
			params['eerror'] = "That's not a valid email"
			if not email=='':
				have_error = True

		if have_error:
			self.render_signup(**params)
		else:
			salt = self.get_salt()
			pass_hash = self.make_pwd_hash(pwd, salt)
			if not email=='':
				ua = UserAccount(username=str(username), password = pass_hash, email=str(email))
			else:
				ua = UserAccount(username=str(username), password = pass_hash)

			ua.put()
			cookie_val = str(username)
			self.response.headers.add_header('Set-Cookie', 'user_id='+cookie_val+'; Path=/')
			self.redirect("/blog/welcome")

class Login(Handler):

	def render_login(self, username="", error=""):
		self.render('login.html', username=username, error=error)


	def get(self):
		self.render_login()

	def post(self):
		params = dict()
		user = self.request.get("username")
		pwd = self.request.get("password")
		user_row = db.GqlQuery("SELECT * FROM UserAccount WHERE username=:1", user)
		for u in user_row:
			fetched_pwd = u.password
			salt = fetched_pwd.split('|')[1]
			pass_hash = make_pwd_hash(str(pwd), str(salt))
			#print pass_hash
			if fetched_pwd==pass_hash:
				cookie_val = str(user)
				self.response.headers.add_header('Set-Cookie', 'user_id='+cookie_val+'; Path=/')
				self.redirect("/blog/welcome")
			else:
				params['username'] = user
				params['error'] = "Invalid username or password"
				self.render_login(**params)



class Welcome(Handler):

	def get(self):
		userid = self.request.cookies.get('user_id')
		if not userid or userid=='':
			self.redirect('/blog/signup')
		else:
			self.response.out.write("<h2>Welcome, %s!</h2>" %userid)

class FlushCache(Handler):
	def get(self):
		memcache.flush_all()
		self.redirect('/blog/')

class Logout(Handler):

	def get(self):
		userid = self.request.cookies.get('user_id')
		userid = ''
		cookie_val = str(userid)
		self.response.headers.add_header('Set-Cookie', 'user_id='+cookie_val+'; Path=/')
		self.redirect("/blog/signup")



app = webapp2.WSGIApplication([('/blog/newpost', NewPost),
								('/blog/signup', Signup),
								('/blog/welcome', Welcome),
								('/blog/login', Login),
								('/blog/logout', Logout),
								('/blog/flush', FlushCache),
								('/blog/?', Blog),
								('/blog/.json', BlogJson),
								('/blog/(.*).json', PermalinkJson),
								('/blog/(.*)', PostHandler)
								],
								debug=True)