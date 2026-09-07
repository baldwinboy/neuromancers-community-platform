---
name: django-rules
description: `rules` is a tiny yet powerful app for handling object-level permissions in Django.
---

rules is a tiny but powerful app providing object-level permissions to Django, without requiring a database. At its core, it is a generic framework for building rule-based systems, similar to [decision trees](http://wikipedia.org/wiki/Decision_tree). It can also be used as a standalone library in other contexts and frameworks.

 [![https://img.shields.io/github/workflow/status/dfunckt/django-rules/CI/master](https://img.shields.io/github/workflow/status/dfunckt/django-rules/CI/master)](https://github.com/dfunckt/django-rules/actions)[![https://coveralls.io/repos/dfunckt/django-rules/badge.svg](https://coveralls.io/repos/dfunckt/django-rules/badge.svg) ](https://coveralls.io/r/dfunckt/django-rules)[![https://img.shields.io/pypi/v/rules.svg](https://img.shields.io/pypi/v/rules.svg) ](https://pypi.org/project/rules/)[![https://img.shields.io/pypi/pyversions/rules.svg](https://img.shields.io/pypi/pyversions/rules.svg) ](https://pypi.org/project/rules/)[![https://img.shields.io/badge/code%20style-black-000000.svg](https://img.shields.io/badge/code%20style-black-000000.svg) ](https://github.com/psf/black)[![https://img.shields.io/badge/pre--commit-enabled-brightgreen?logo=pre-commit&logoColor=white](https://img.shields.io/badge/pre--commit-enabled-brightgreen?logo=pre-commit&logoColor=white)](https://github.com/pre-commit/pre-commit)

Features
--------

rules has got you covered. rules is:

*   **Documented**, **tested**, **reliable** and **easy to use**.
    
*   **Versatile**. Decorate callables to build complex graphs of predicates. Predicates can be any type of callable -- simple functions, lambdas, methods, callable class objects, partial functions, decorated functions, anything really.
    
*   **A good Django citizen**. Seamless integration with Django views, templates and the Admin for testing for object-level permissions.
    
*   **Efficient** and **smart**. No need to mess around with a database to figure out whether John really wrote that book.
    
*   **Simple**. Dive in the code. You'll need 10 minutes to figure out how it works.
    
*   **Powerful**. rules comes complete with advanced features, such as invocation context and storage for arbitrary data, skipping evaluation of predicates under specific conditions, logging of evaluated predicates and more!
    

Table of Contents
-----------------

*   [Requirements](#requirements)
    
*   [Upgrading from 2.x](#upgrading-from-2-x)
    
*   [Upgrading from 1.x](#upgrading-from-1-x)
    
*   [How to install](#how-to-install)
    
    *   [Configuring Django](#configuring-django)
        
*   [Using Rules](#using-rules)
    
    *   [Creating predicates](#creating-predicates)
        
    *   [Dynamic predicates](#dynamic-predicates)
        
    *   [Setting up rules](#setting-up-rules)
        
    *   [Combining predicates](#combining-predicates)
        
*   [Using Rules with Django](#using-rules-with-django)
    
    *   [Permissions](#permissions)
        
    *   [Permissions in models](#permissions-in-models)
        
    *   [Permissions in views](#permissions-in-views)
        
    *   [Permissions and rules in templates](#permissions-and-rules-in-templates)
        
    *   [Permissions in the Admin](#permissions-in-the-admin)
        
    *   [Permissions in Django Rest Framework](#permissions-in-django-rest-framework)
        
*   [Advanced features](#advanced-features)
    
    *   [Custom rule sets](#custom-rule-sets)
        
    *   [Invocation context](#invocation-context)
        
    *   [Binding "self"](#binding-self)
        
    *   [Skipping predicates](#skipping-predicates)
        
    *   [Logging predicate evaluation](#logging-predicate-evaluation)
        
*   [Best practices](#best-practices)
    
*   [API Reference](#api-reference)
    
*   [Licence](#licence)
    

Requirements
------------

rules requires Python 3.8 or newer. The last version to support Python 2.7 is rules 2.2. It can optionally integrate with Django, in which case requires Django 3.2 or newer.

_Note_: At any given moment in time, rules will maintain support for all currently supported Django versions, while dropping support for those versions that reached end-of-life in minor releases. See the [Supported Versions](https://www.djangoproject.com/download/#supported-versions) section on Django Project website for the current state and timeline.

Upgrading from 2.x
------------------

The are no significant changes between rules 2.x and 3.x except dropping support for Python 2, so before upgrading to 3.x you just need to make sure you're running a supported Python 3 version.

Upgrading from 1.x
------------------

*   Support for Python 2.6 and 3.3, and Django versions before 1.11 has been dropped.
    
*   The SkipPredicate exception and skip() method of Predicate, that were used to signify that a predicate should be skipped, have been removed. You may return None from your predicate to achieve this.
    
*   The APIs to replace a rule's predicate have been renamed and their behaviour changed. replace\_rule and replace\_perm functions and replace\_rule method of RuleSet have been renamed to set\_rule, set\_perm and RuleSet.set\_perm respectively. The old behaviour was to raise a KeyError if a rule by the given name did not exist. Since version 2.0 this has changed and you can safely use set\_\* to set a rule's predicate without having to ensure the rule exists first.
    

How to install
--------------

Using pip:

    $ pip install rules

Manually:

    $ git clone https://github.com/dfunckt/django-rules.git
    $ cd django-rules
    $ python setup.py install

Run tests with:

    $ ./runtests.sh

You may also want to read [Best practices](#best-practices) for general advice on how to use rules.

### Configuring Django

Add rules to INSTALLED\_APPS:

    INSTALLED_APPS = (
        # ...
        'rules',
    )

Add the authentication backend:

    AUTHENTICATION_BACKENDS = (
        'rules.permissions.ObjectPermissionBackend',
        'django.contrib.auth.backends.ModelBackend',
    )

Using Rules
-----------

rules is based on the idea that you maintain a dict-like object that maps string keys used as identifiers of some kind, to callables, called _predicates_. This dict-like object is actually an instance of RuleSet and the predicates are instances of Predicate.

### Creating predicates

Let's ignore rule sets for a moment and go ahead and define a predicate. The easiest way is with the @predicate decorator:

    >>> @rules.predicate
    >>> def is_book_author(user, book):
    ...     return book.author == user
    ...
    >>> is_book_author
    <Predicate:is_book_author object at 0x10eeaa490>

This predicate will return True if the book's author is the given user, False otherwise.

Predicates can be created from any callable that accepts anything from zero to two positional arguments:

*   fn(obj, target)
    
*   fn(obj)
    
*   fn()
    

This is their generic form. If seen from the perspective of authorization in Django, the equivalent signatures are:

*   fn(user, obj)
    
*   fn(user)
    
*   fn()
    

Predicates can do pretty much anything with the given arguments, but must always return True if the condition they check is true, False otherwise. rules comes with several predefined predicates that you may read about later on in [API Reference](#api-reference), that are mostly useful when dealing with [authorization in Django](#authorization-in-django).

### Dynamic predicates

If needed predicates can be created dynamically depending on parameters:

    import rules
    
    
    def role_is(role_id):
        @rules.predicate
        def user_has_role(user):
            return user.role.id == role_id
    
        return user_has_role
    
    
    rules.add_perm("reports.view_report_abc", role_is(12))
    rules.add_perm("reports.view_report_xyz", role_is(13))

### Setting up rules

Let's pretend that we want to let authors edit or delete their books, but not books written by other authors. So, essentially, what determines whether an author _can edit_ or _can delete_ a given book is _whether they are its author_.

In rules, such requirements are modelled as _rules_. A _rule_ is a map of a unique identifier (eg. "can edit") to a predicate. Rules are grouped together into a _rule set_. rules has two predefined rule sets:

*   A default rule set storing shared rules.
    
*   Another rule set storing rules that serve as permissions in a Django context.
    

So, let's define our first couple of rules, adding them to the shared rule set. We can use the is\_book\_author predicate we defined earlier:

    >>> rules.add_rule('can_edit_book', is_book_author)
    >>> rules.add_rule('can_delete_book', is_book_author)

Assuming we've got some data, we can now test our rules:

    >>> from django.contrib.auth.models import User
    >>> from books.models import Book
    >>> guidetodjango = Book.objects.get(isbn='978-1-4302-1936-1')
    >>> guidetodjango.author
    <User: adrian>
    >>> adrian = User.objects.get(username='adrian')
    >>> rules.test_rule('can_edit_book', adrian, guidetodjango)
    True
    >>> rules.test_rule('can_delete_book', adrian, guidetodjango)
    True

Nice... but not awesome.

### Combining predicates

Predicates by themselves are not so useful -- not more useful than any other function would be. Predicates, however, can be combined using binary operators to create more complex ones. Predicates support the following operators:

*   P1 & P2: Returns a new predicate that returns True if _both_ predicates return True, otherwise False. If P1 returns False, P2 will not be evaluated.
    
*   P1 | P2: Returns a new predicate that returns True if _any_ of the predicates returns True, otherwise False. If P1 returns True, P2 will not be evaluated.
    
*   P1 ^ P2: Returns a new predicate that returns True if one of the predicates returns True and the other returns False, otherwise False.
    
*   ~P: Returns a new predicate that returns the negated result of the original predicate.
    

Suppose the requirement for allowing a user to edit a given book was for them to be either the book's author, or a member of the "editors" group. Allowing users to delete a book should still be determined by whether the user is the book's author.

With rules that's easy to implement. We'd have to define another predicate, that would return True if the given user is a member of the "editors" group, False otherwise. The built-in is\_group\_member factory will come in handy:

    >>> is_editor = rules.is_group_member('editors')
    >>> is_editor
    <Predicate:is_group_member:editors object at 0x10eee1350>

We could combine it with the is\_book\_author predicate to create a new one that checks for either condition:

    >>> is_book_author_or_editor = is_book_author | is_editor
    >>> is_book_author_or_editor
    <Predicate:(is_book_author | is_group_member:editors) object at 0x10eee1390>

We can now update our can\_edit\_book rule:

    >>> rules.set_rule('can_edit_book', is_book_author_or_editor)
    >>> rules.test_rule('can_edit_book', adrian, guidetodjango)
    True
    >>> rules.test_rule('can_delete_book', adrian, guidetodjango)
    True

Let's see what happens with another user:

    >>> martin = User.objects.get(username='martin')
    >>> list(martin.groups.values_list('name', flat=True))
    ['editors']
    >>> rules.test_rule('can_edit_book', martin, guidetodjango)
    True
    >>> rules.test_rule('can_delete_book', martin, guidetodjango)
    False

Awesome.

So far, we've only used the underlying, generic framework for defining and testing rules. This layer is not at all specific to Django; it may be used in any context. There's actually no import of anything Django-related in the whole app (except in the rules.templatetags module). rules however can integrate tightly with Django to provide authorization.

Using Rules with Django
-----------------------

rules is able to provide object-level permissions in Django. It comes with an authorization backend and a couple template tags for use in your templates.

### Permissions

In rules, permissions are a specialised type of rules. You still define rules by creating and combining predicates. These rules however, must be added to a permissions-specific rule set that comes with rules so that they can be picked up by the rules authorization backend.

#### Creating permissions

The convention for naming permissions in Django is app\_label.action\_object, and we like to adhere to that. Let's add rules for the books.change\_book and books.delete\_book permissions:

    >>> rules.add_perm('books.change_book', is_book_author | is_editor)
    >>> rules.add_perm('books.delete_book', is_book_author)

See the difference in the API? add\_perm adds to a permissions-specific rule set, whereas add\_rule adds to a default shared rule set. It's important to know however, that these two rule sets are separate, meaning that adding a rule in one does not make it available to the other.

#### Checking for permission

Let's go ahead and check whether adrian has change permission to the guidetodjango book:

    >>> adrian.has_perm('books.change_book', guidetodjango)
    False

When you call the User.has\_perm method, Django asks each backend in settings.AUTHENTICATION\_BACKENDS whether a user has the given permission for the object. When queried for object permissions, Django's default authentication backend always returns False. rules comes with an authorization backend, that is able to provide object-level permissions by looking into the permissions-specific rule set.

Let's add the rules authorization backend in settings:

    AUTHENTICATION_BACKENDS = (
        'rules.permissions.ObjectPermissionBackend',
        'django.contrib.auth.backends.ModelBackend',
    )

Now, checking again gives adrian the required permissions:

    >>> adrian.has_perm('books.change_book', guidetodjango)
    True
    >>> adrian.has_perm('books.delete_book', guidetodjango)
    True
    >>> martin.has_perm('books.change_book', guidetodjango)
    True
    >>> martin.has_perm('books.delete_book', guidetodjango)
    False

**NOTE:** Calling has\_perm on a superuser will ALWAYS return True.

### Permissions in models

**NOTE:** The features described in this section work on Python 3+ only.

It is common to have a set of permissions for a model, like what Django offers with its default model permissions (such as _add_, _change_ etc.). When using rules as the permission checking backend, you can declare object-level permissions for any model in a similar way, using a new Meta option.

First, you need to switch your model's base and metaclass to the slightly extended versions provided in rules.contrib.models. There are several classes and mixins you can use, depending on whether you're already using a custom base and/or metaclass for your models or not. The extensions are very slim and don't affect the models' behavior in any way other than making it register permissions.

*   If you're using the stock django.db.models.Model as base for your models, simply switch over to RulesModel and you're good to go.
    
*   If you already have a custom base class adding common functionality to your models, add RulesModelMixin to the classes it inherits from and set RulesModelBase as its metaclass, like so:
    
    from django.db.models import Model
    from rules.contrib.models import RulesModelBase, RulesModelMixin
    
    class MyModel(RulesModelMixin, Model, metaclass=RulesModelBase):
        ...
    
*   If you're using a custom metaclass for your models, you'll already know how to make it inherit from RulesModelBaseMixin yourself.
    

Then, create your models like so, assuming you're using RulesModel as base directly:

import rules
from rules.contrib.models import RulesModel

class Book(RulesModel):
    class Meta:
        rules\_permissions = {
            "add": rules.is\_staff,
            "read": rules.is\_authenticated,
        }

This would be equivalent to the following calls:

rules.add\_perm("app\_label.add\_book", rules.is\_staff)
rules.add\_perm("app\_label.read\_book", rules.is\_authenticated)

There are methods in RulesModelMixin that you can overwrite in order to customize how a model's permissions are registered. See the documented source code for details if you need this.

Of special interest is the get\_perm classmethod of RulesModelMixin, which can be used to convert a permission type to the corresponding full permission name. If you need to query for some type of permission on a given model programmatically, this is handy:

if user.has\_perm(Book.get\_perm("read")):
    ...

### Permissions in views

rules comes with a set of view decorators to help you enforce authorization in your views.

#### Using the function-based view decorator

For function-based views you can use the permission\_required decorator:

    from django.shortcuts import get_object_or_404
    from rules.contrib.views import permission_required
    from posts.models import Post
    
    def get_post_by_pk(request, post_id):
        return get_object_or_404(Post, pk=post_id)
    
    @permission_required('posts.change_post', fn=get_post_by_pk)
    def post_update(request, post_id):
        # ...

Usage is straight-forward, but there's one thing in the example above that stands out and this is the get\_post\_by\_pk function. This function, given the current request and all arguments passed to the view, is responsible for fetching and returning the object to check permissions against -- i.e. the Post instance with PK equal to the given post\_id in the example. This specific use-case is quite common so, to save you some typing, rules comes with a generic helper function that you can use to do this declaratively. The example below is equivalent to the one above:

    from rules.contrib.views import permission_required, objectgetter
    from posts.models import Post
    
    @permission_required('posts.change_post', fn=objectgetter(Post, 'post_id'))
    def post_update(request, post_id):
        # ...

For more information on the decorator and helper function, refer to the rules.contrib.views module.

#### Using the class-based view mixin

Django includes a set of access mixins that you can use in your class-based views to enforce authorization. rules extends this framework to provide object-level permissions via a mixin, PermissionRequiredMixin.

The following example will automatically test for permission against the instance returned by the view's get\_object method:

    from django.views.generic.edit import UpdateView
    from rules.contrib.views import PermissionRequiredMixin
    from posts.models import Post
    
    class PostUpdate(PermissionRequiredMixin, UpdateView):
        model = Post
        permission_required = 'posts.change_post'

You can customise the object either by overriding get\_object or get\_permission\_object.

For more information refer to the [Django documentation](https://docs.djangoproject.com/en/stable/topics/auth/default/#limiting-access-to-logged-in-users) and the rules.contrib.views module.

#### Checking permission automatically based on view type

If you use the mechanisms provided by rules.contrib.models to register permissions for your models as described in [Permissions in models](#permissions-in-models), there's another convenient mixin for class-based views available for you.

rules.contrib.views.AutoPermissionRequiredMixin can recognize the type of view it's used with and check for the corresponding permission automatically.

This example view would, without any further configuration, automatically check for the "posts.change\_post" permission, given that the app label is "posts":

from django.views.generic import UpdateView
from rules.contrib.views import AutoPermissionRequiredMixin
from posts.models import Post

class UpdatePostView(AutoPermissionRequiredMixin, UpdateView):
    model = Post

By default, the generic CRUD views from django.views.generic are mapped to the native Django permission types (_add_, _change_, _delete_ and _view_). However, the pre-defined mappings can be extended, changed or replaced altogether when subclassing AutoPermissionRequiredMixin. See the fully documented source code for details on how to do that properly.

### Permissions and rules in templates

rules comes with two template tags to allow you to test for rules and permissions in templates.

Add rules to your INSTALLED\_APPS:

    INSTALLED_APPS = (
        # ...
        'rules',
    )

Then, in your template:

{% load rules %}

{% has\_perm 'books.change\_book' author book as can\_edit\_book %}
{% if can\_edit\_book %}
    ...
{% endif %}

{% test\_rule 'has\_super\_feature' user as has\_super\_feature %}
{% if has\_super\_feature %}
    ...
{% endif %}

### Permissions in the Admin

If you've setup rules to be used with permissions in Django, you're almost set to also use rules to authorize any add/change/delete actions in the Admin. The Admin asks for _four_ different permissions, depending on action:

*   <app\_label>.add\_<modelname>
    
*   <app\_label>.view\_<modelname>
    
*   <app\_label>.change\_<modelname>
    
*   <app\_label>.delete\_<modelname>
    
*   <app\_label>
    

_Note:_ view permission is new in Django v2.1 and should not be added in versions before that.

The first four are obvious. The fifth is the required permission for an app to be displayed in the Admin's "dashboard". Overriding it does not restrict access to the add, change or delete views. Here's some rules for our imaginary books app as an example:

    >>> rules.add_perm('books', rules.always_allow)
    >>> rules.add_perm('books.add_book', is_staff)
    >>> rules.add_perm('books.view_book', is_staff | has_secret_access_code)
    >>> rules.add_perm('books.change_book', is_staff)
    >>> rules.add_perm('books.delete_book', is_staff)

Django Admin does not support object-permissions, in the sense that it will never ask for permission to perform an action _on an object_, only whether a user is allowed to act on (_any_) instances of a model.

If you'd like to tell Django whether a user has permissions on a specific object, you'd have to override the following methods of a model's ModelAdmin:

*   has\_view\_permission(user, obj=None)
    
*   has\_change\_permission(user, obj=None)
    
*   has\_delete\_permission(user, obj=None)
    

rules comes with a custom ModelAdmin subclass, rules.contrib.admin.ObjectPermissionsModelAdmin, that overrides these methods to pass on the edited model instance to the authorization backends, thus enabling permissions per object in the Admin:

    # books/admin.py
    from django.contrib import admin
    from rules.contrib.admin import ObjectPermissionsModelAdmin
    from .models import Book
    
    class BookAdmin(ObjectPermissionsModelAdmin):
        pass
    
    admin.site.register(Book, BookAdmin)

Now this allows you to specify permissions like this:

    >>> rules.add_perm('books', rules.always_allow)
    >>> rules.add_perm('books.add_book', has_author_profile)
    >>> rules.add_perm('books.change_book', is_book_author_or_editor)
    >>> rules.add_perm('books.delete_book', is_book_author)

To preserve backwards compatibility, Django will ask for either _view_ or _change_ permission. For maximum flexibility, rules behaves subtly different: rules will ask for the change permission if and only if no rule exists for the view permission.

### Permissions in Django Rest Framework

Similar to rules.contrib.views.AutoPermissionRequiredMixin, there is a rules.contrib.rest\_framework.AutoPermissionViewSetMixin for viewsets in Django Rest Framework. The difference is that it doesn't derive permission from the type of view but from the API action (_create_, _retrieve_ etc.) that's tried to be performed. Of course, it also requires you to declare your models as described in [Permissions in models](#permissions-in-models).

Here is a possible ModelViewSet for the Post model with fully automated CRUD permission checking:

from rest\_framework.serializers import ModelSerializer
from rest\_framework.viewsets import ModelViewSet
from rules.contrib.rest\_framework import AutoPermissionViewSetMixin
from posts.models import Post

class PostSerializer(ModelSerializer):
    class Meta:
        model = Post
        fields = "\_\_all\_\_"

class PostViewSet(AutoPermissionViewSetMixin, ModelViewSet):
    queryset = Post.objects.all()
    serializer\_class = PostSerializer

By default, the CRUD actions of ModelViewSet are mapped to the native Django permission types (_add_, _change_, _delete_ and _view_). The list action has no permission checking enabled. However, the pre-defined mappings can be extended, changed or replaced altogether when using (or subclassing) AutoPermissionViewSetMixin. Custom API actions defined via the @action decorator may then be mapped as well. See the fully documented source code for details on how to properly customize the default behavior.

Advanced features
-----------------

### Custom rule sets

You may create as many rule sets as you need:

    >>> features = rules.RuleSet()

And manipulate them by adding, removing, querying and testing rules:

    >>> features.rule_exists('has_super_feature')
    False
    >>> is_special_user = rules.is_group_member('special')
    >>> features.add_rule('has_super_feature', is_special_user)
    >>> 'has_super_feature' in features
    True
    >>> features['has_super_feature']
    <Predicate:is_group_member:special object at 0x10eeaa500>
    >>> features.test_rule('has_super_feature', adrian)
    True
    >>> features.remove_rule('has_super_feature')

Note however that custom rule sets are _not available_ in Django templates -- you need to provide integration yourself.

### Invocation context

A new context is created as a result of invoking Predicate.test() and is only valid for the duration of the invocation. A context is a simple dict that you can use to store arbitrary data, (eg. caching computed values, setting flags, etc.), that can be used by predicates later on in the chain. Inside a predicate function it can be used like so:

    >>> @predicate
    ... def mypred(a, b):
    ...     value = compute_expensive_value(a)
    ...     mypred.context['value'] = value
    ...     return True

Other predicates can later use stored values:

    >>> @predicate
    ... def myotherpred(a, b):
    ...     value = myotherpred.context.get('value')
    ...     if value is not None:
    ...         return do_something_with_value(value)
    ...     else:
    ...         return do_something_without_value()

Predicate.context provides a single args attribute that contains the arguments as given to test() at the beginning of the invocation.

### Binding "self"

In a predicate's function body, you can refer to the predicate instance itself by its name, eg. is\_book\_author. Passing bind=True as a keyword argument to the predicate decorator will let you refer to the predicate with self, which is more convenient. Binding self is just syntactic sugar. As a matter of fact, the following two are equivalent:

    >>> @predicate
    ... def is_book_author(user, book):
    ...     if is_book_author.context.args:
    ...         return user == book.author
    ...     return False
    
    >>> @predicate(bind=True)
    ... def is_book_author(self, user, book):
    ...     if self.context.args:
    ...         return user == book.author
    ...     return False

### Skipping predicates

You may skip evaluation by returning None from your predicate:

    >>> @predicate(bind=True)
    ... def is_book_author(self, user, book):
    ...     if len(self.context.args) > 1:
    ...         return user == book.author
    ...     else:
    ...         return None

Returning None signifies that the predicate need not be evaluated, thus leaving the predicate result up to that point unchanged.

### Logging predicate evaluation

rules can optionally be configured to log debug information as rules are evaluated to help with debugging your predicates. Messages are sent at the DEBUG level to the 'rules' logger. The following [dictConfig](https://docs.python.org/3.6/library/logging.config.html#logging-config-dictschema) configures a console logger (place this in your project's settings.py if you're using rules with Django):

    LOGGING = {
        'version': 1,
        'disable_existing_loggers': False,
        'handlers': {
            'console': {
                'level': 'DEBUG',
                'class': 'logging.StreamHandler',
            },
        },
        'loggers': {
            'rules': {
                'handlers': ['console'],
                'level': 'DEBUG',
                'propagate': True,
            },
        },
    }

When this logger is active each individual predicate will have a log message printed when it is evaluated.

Best practices
--------------

Before you can test for rules, these rules must be registered with a rule set, and for this to happen the modules containing your rule definitions must be imported.

For complex projects with several predicates and rules, it may not be practical to define all your predicates and rules inside one module. It might be best to split them among any sub-components of your project. In a Django context, these sub-components could be the apps for your project.

On the other hand, because importing predicates from all over the place in order to define rules can lead to circular imports and broken hearts, it's best to further split predicates and rules in different modules.

rules may optionally be configured to autodiscover rules.py modules in your apps and import them at startup. To have rules do so, just edit your INSTALLED\_APPS setting:

    INSTALLED_APPS = (
        # replace 'rules' with:
        'rules.apps.AutodiscoverRulesConfig',
    )

**Note:** On Python 2, you must also add the following to the top of your rules.py file, or you'll get import errors trying to import rules itself:

    from __future__ import absolute_import

API Reference
-------------

The core APIs are accessible from the root rules module. Django-specific functionality for the Admin and views is available from rules.contrib.

### Class rules.Predicate

You create Predicate instances by passing in a callable:

    >>> def is_book_author(user, book):
    ...     return book.author == user
    ...
    >>> pred = Predicate(is_book_author)
    >>> pred
    <Predicate:is_book_author object at 0x10eeaa490>

You may optionally provide a different name for the predicate that is used when inspecting it:

    >>> pred = Predicate(is_book_author, name='another_name')
    >>> pred
    <Predicate:another_name object at 0x10eeaa490>

Also, you may optionally provide bind=True in order to be able to access the predicate instance with self:

    >>> def is_book_author(self, user, book):
    ...     if self.context.args:
    ...         return user == book.author
    ...     return False
    ...
    >>> pred = Predicate(is_book_author, bind=True)
    >>> pred
    <Predicate:is_book_author object at 0x10eeaa490>

#### Instance methods

test(obj=None, target=None)

Returns the result of calling the passed in callable with zero, one or two positional arguments, depending on how many it accepts.

### Class rules.RuleSet

RuleSet extends Python's built-in [dict](http://docs.python.org/library/stdtypes.html#mapping-types-dict) type. Therefore, you may create and use a rule set any way you'd use a dict.

#### Instance methods

add\_rule(name, predicate)

Adds a predicate to the rule set, assigning it to the given rule name. Raises KeyError if another rule with that name already exists.

set\_rule(name, predicate)

Set the rule with the given name, regardless if one already exists.

remove\_rule(name)

Remove the rule with the given name. Raises KeyError if a rule with that name does not exist.

rule\_exists(name)

Returns True if a rule with the given name exists, False otherwise.

test\_rule(name, obj=None, target=None)

Returns the result of calling predicate.test(obj, target) where predicate is the predicate for the rule with the given name. Returns False if a rule with the given name does not exist.

### Decorators

@predicate

Decorator that creates a predicate out of any callable:

    >>> @predicate
    ... def is_book_author(user, book):
    ...     return book.author == user
    ...
    >>> is_book_author
    <Predicate:is_book_author object at 0x10eeaa490>

Customising the predicate name:

    >>> @predicate(name='another_name')
    ... def is_book_author(user, book):
    ...     return book.author == user
    ...
    >>> is_book_author
    <Predicate:another_name object at 0x10eeaa490>

Binding self:

    >>> @predicate(bind=True)
    ... def is_book_author(self, user, book):
    ...     if 'user_has_special_flag' in self.context:
    ...         return self.context['user_has_special_flag']
    ...     return book.author == user

### Predefined predicates

always\_allow(), always\_true()

Always returns True.

always\_deny(), always\_false()

Always returns False.

is\_authenticated(user)

Returns the result of calling user.is\_authenticated(). Returns False if the given user does not have an is\_authenticated method.

is\_superuser(user)

Returns the result of calling user.is\_superuser. Returns False if the given user does not have an is\_superuser property.

is\_staff(user)

Returns the result of calling user.is\_staff. Returns False if the given user does not have an is\_staff property.

is\_active(user)

Returns the result of calling user.is\_active. Returns False if the given user does not have an is\_active property.

is\_group\_member(\*groups)

Factory that creates a new predicate that returns True if the given user is a member of _all_ the given groups, False otherwise.

### Shortcuts

#### Managing the shared rule set

add\_rule(name, predicate)

Adds a rule to the shared rule set. See RuleSet.add\_rule.

set\_rule(name, predicate)

Set the rule with the given name from the shared rule set. See RuleSet.set\_rule.

remove\_rule(name)

Remove a rule from the shared rule set. See RuleSet.remove\_rule.

rule\_exists(name)

Returns whether a rule exists in the shared rule set. See RuleSet.rule\_exists.

test\_rule(name, obj=None, target=None)

Tests the rule with the given name. See RuleSet.test\_rule.

#### Managing the permissions rule set

add\_perm(name, predicate)

Adds a rule to the permissions rule set. See RuleSet.add\_rule.

set\_perm(name, predicate)

Replace a rule from the permissions rule set. See RuleSet.set\_rule.

remove\_perm(name)

Remove a rule from the permissions rule set. See RuleSet.remove\_rule.

perm\_exists(name)

Returns whether a rule exists in the permissions rule set. See RuleSet.rule\_exists.

has\_perm(name, user=None, obj=None)

Tests the rule with the given name. See RuleSet.test\_rule.

Licence
-------

django-rules is distributed under the MIT licence.

Copyright (c) 2014 Akis Kesoglou

Permission is hereby granted, free of charge, to any person obtaining a copy of this software and associated documentation files (the "Software"), to deal in the Software without restriction, including without limitation the rights to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the Software, and to permit persons to whom the Software is furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.