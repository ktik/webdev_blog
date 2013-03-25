import webapp2
import jinja2
import os
import re

from google.appengine.ext import db

jinja_environment = jinja2.Environment(
    loader=jinja2.FileSystemLoader(os.path.dirname(__file__)), autoescape=True)

USER_RE = re.compile(r"^[a-zA-Z0-9_-]{3,20}$")
PASS_RE = re.compile(r"^.{3,20}$")
EMAIL_RE = re.compile(r"^[\S]+@[\S]+\.[\S]+$")

def valid_username(username):
    return username and USER_RE.match(username)

def valid_password(pwd):
    return pwd and PASS_RE.match(pwd)

def valid_email(email):
    return not email or EMAIL_RE.match(email)

class Entry(db.Model):
	entry_id = db.IntegerProperty()
	subject = db.StringProperty(required = True)
	content = db.TextProperty(required = True)
	created = db.DateTimeProperty(auto_now_add = True)

class Useraccount(db.Model):
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
			mykey = str(e.key())
			self.redirect("/blog/%s" %mykey)
			#self.write("thanks!")
		else:
			error = "We need a subject and an entry"
			self.render_newpost(subject, content, error)

class Blog(Handler):
	def get(self):
		posts = db.GqlQuery("SELECT * FROM Entry ORDER BY created DESC")
		self.render("blog.html", posts=posts)

class PostHandler(Handler):
	def get(self, post_id):
		#self.write("Hello!")
		post = Entry.get(post_id)
		self.render("post.html", post=post)

class Signup(Handler):

	def render_signup(self, username="", email="", uerror="", perror="", eerror=""):
	#def render_signup(self, **kw):
		self.render("signup.html", username=username, email=email, uerror=uerror, perror=perror, eerror=eerror)
	
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
			have_error = True

		if have_error:
			self.render_signup(**params)
		else:
			cookie_val = str(username)
			self.response.headers.add_header('Set-Cookie', 'user_id='+cookie_val+'; Path=/')
			self.redirect("/blog/welcome")

class Welcome(Handler):

	def get(self):
		userid = self.request.cookies.get('user_id')
		self.response.out.write("Welcome, %s" %userid)




app = webapp2.WSGIApplication([('/blog/newpost', NewPost),
								('/blog/signup', Signup),
								('/blog/welcome', Welcome),
								('/blog', Blog),
								('/blog/(.*)', PostHandler)
								],
								debug=True)