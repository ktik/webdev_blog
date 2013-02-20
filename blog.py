import webapp2
import jinja2
import os

from google.appengine.ext import db

jinja_environment = jinja2.Environment(
    loader=jinja2.FileSystemLoader(os.path.dirname(__file__)), autoescape=True)

class Entry(db.Model):
	entry_id = db.IntegerProperty()
	subject = db.StringProperty(required = True)
	content = db.TextProperty(required = True)
	created = db.DateTimeProperty(auto_now_add = True)

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



app = webapp2.WSGIApplication([('/blog/newpost', NewPost),
								('/blog', Blog),
								('/blog/(.*)', PostHandler)
								],
								debug=True)