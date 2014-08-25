"""
Some models for pulling data from Trac.

Initially generated by inspectdb then modified heavily by hand, often by
consulting http://trac.edgewall.org/wiki/TracDev/DatabaseSchema.

These are far from perfect: many (most?) Trac tables have composite primary
keys, which Django can't represent. This means a lot of built-in Django stuff
(the admin, for example) won't work at all with these models. I haven't
investigated just how deeply down thess failures go, but I suspect all sorts
of things just won't work.

However, they're Good Enough(tm) to let me pull some basic (read-only) data out,
and that's all I really need.

Some potential TODOs:

    * Add some convienance manager functions to deal with ticket_custom. Right
      now you can query with a join::

            Ticket.objects.filter(custom_fields__name='ui_ux',
                                  custom_fields__value='1')

      Perhaps we might be able to get something like::

            Ticket.objects.with_custom(ui_ux=True)

      Or even a custom .filter() that intercepts and figures it out?

    * Trac stores SVN repository revisions as '0000003744' grar. This
      makes querying awkward. There's probably some tricky manager manger
      that we could do here.

    * The whole Revision model will fall apart if we ever had a second
      repository to Trac.

And a few notes on tables that're left out and why:

    * All the session and permission tables: they're just not needd.

    * Enum: I don't know what this is or what it's for.

    * NodeChange: Ditto.

"""
from __future__ import unicode_literals

import datetime

from django.db import models
from django.utils.tzinfo import FixedOffset


_epoc = datetime.datetime(1970, 1, 1, tzinfo=FixedOffset(0))


class time_property(object):
    """
    Convert Trac timestamps into UTC datetimes.

    See http://trac.edgewall.org/browser//branches/0.12-stable/trac/util/datefmt.py
    for Trac's version of all this. Mine's something of a simplification.

    Like the rest of this module this is far from perfect -- no setters, for
    example! That's good enough for now.
    """
    def __init__(self, fieldname):
        self.fieldname = fieldname

    def __get__(self, instance, owner):
        if instance is None:
            return self
        timestamp = getattr(instance, self.fieldname)
        return _epoc + datetime.timedelta(microseconds=timestamp)


class Ticket(models.Model):
    id = models.IntegerField(primary_key=True)
    type = models.TextField()

    _time = models.BigIntegerField(db_column='time')
    time = time_property('_time')

    _changetime = models.BigIntegerField(db_column='changetime')
    changetime = time_property('_changetime')

    component = models.ForeignKey('Component', related_name='tickets', db_column='component')
    severity = models.TextField()
    owner = models.TextField()
    reporter = models.TextField()
    cc = models.TextField()
    version = models.ForeignKey('Version', related_name='tickets', db_column='version')
    milestone = models.ForeignKey('Milestone', related_name='tickets', db_column='milestone')
    priority = models.TextField()
    status = models.TextField()
    resolution = models.TextField()
    summary = models.TextField()
    description = models.TextField()
    keywords = models.TextField()

    class Meta(object):
        db_table = 'ticket'
        managed = False

    def __unicode__(self):
        return "#%s: %s" % (self.id, self.summary)

    def __init__(self, *args, **kwargs):
        super(Ticket, self).__init__(*args, **kwargs)

        # Munge custom fields onto this object. This sucks since it implies
        # querying will work (it won't!) and that writing will work (ditto).
        # Also notice that *nasty* mapping of Trac's "booleanish" things to
        # real booleans. This can fail in a bunch of ways, but not in our
        # particular install.
        for name, value in self.custom_fields.values_list('name', 'value'):
            if value in ('0', '1'):
                value = bool(int(value))
            setattr(self, name, value)


class TicketCustom(models.Model):
    ticket = models.ForeignKey(Ticket, related_name='custom_fields', db_column='ticket', primary_key=True)
    name = models.TextField()
    value = models.TextField()

    class Meta(object):
        db_table = 'ticket_custom'
        managed = False

    def __unicode__(self):
        return "%s: %s" % (self.name, self.value)


class TicketChange(models.Model):
    ticket = models.ForeignKey(Ticket, related_name='changes', db_column='ticket', primary_key=True)
    author = models.TextField()
    field = models.TextField()
    oldvalue = models.TextField()
    newvalue = models.TextField()

    _time = models.BigIntegerField(db_column='time')
    time = time_property('_time')

    class Meta(object):
        db_table = 'ticket_change'
        managed = False
        ordering = ['_time']

    def __unicode__(self):
        return "#%s: changed %s" % (self.ticket.id, self.field)


class Component(models.Model):
    name = models.TextField(primary_key=True)
    owner = models.TextField()
    description = models.TextField()

    class Meta(object):
        db_table = 'component'
        managed = False

    def __unicode__(self):
        return self.name


class Version(models.Model):
    name = models.TextField(primary_key=True)
    description = models.TextField()

    _time = models.BigIntegerField(db_column='time')
    time = time_property('_time')

    class Meta(object):
        db_table = 'version'
        managed = False

    def __unicode__(self):
        return self.name


class Milestone(models.Model):
    name = models.TextField(primary_key=True)
    description = models.TextField()

    _due = models.BigIntegerField(db_column='_due')
    due = time_property('due')

    _completed = models.BigIntegerField(db_column='_completed')
    completed = time_property('completed')

    class Meta(object):
        db_table = 'milestone'
        managed = False

    def __unicode__(self):
        return self.name


class SingleRepoRevisionManager(models.Manager):
    """
    Forces Revision to only query against a single repo, thus making
    Revision.rev behave something like a primary key.
    """
    def __init__(self, repo_id):
        self.repo_id = repo_id
        super(SingleRepoRevisionManager, self).__init__()

    def get_queryset(self):
        qs = super(SingleRepoRevisionManager, self).get_queryset()
        return qs.filter(repos=self.repo_id)


SINGLE_REPO_ID = 1


class Revision(models.Model):
    repos = models.IntegerField()
    rev = models.TextField(primary_key=True)

    _time = models.BigIntegerField(db_column='time')
    time = time_property('time')

    author = models.TextField()
    message = models.TextField()

    objects = SingleRepoRevisionManager(repo_id=SINGLE_REPO_ID)

    class Meta(object):
        db_table = 'revision'
        managed = False

    def __unicode__(self):
        return '[%s] %s' % (self.rev, self.message.split('\n', 1)[0])


# The Wiki table uses a composite primary key (name, version). Since
# Django doesn't support this, this model sits on top of a simple view.
class Wiki(models.Model):
    django_id = models.TextField(primary_key=True)
    name = models.TextField()
    version = models.IntegerField()
    _time = models.BigIntegerField(db_column='time')
    time = time_property('time')
    author = models.TextField()
    ipnr = models.TextField()
    text = models.TextField()
    comment = models.TextField()
    readonly = models.IntegerField()

    class Meta:
        db_table = 'wiki_django_view'
        managed = False

    def __unicode__(self):
        return '%s (v%s)' % (self.name, self.version)


# Same story as for Wiki: attachment's PK is (type, id, filename), so again
# there's a simple view this is on top of.
class Attachment(models.Model):
    django_id = models.TextField(primary_key=True)
    type = models.TextField()
    id = models.TextField()
    filename = models.TextField()
    size = models.IntegerField()
    _time = models.BigIntegerField(db_column='time')
    time = time_property('time')
    description = models.TextField()
    author = models.TextField()
    ipnr = models.TextField()

    class Meta:
        db_table = 'attachment_django_view'
        managed = False

    def __unicode__(self):
        attached_to = ('#%s' % self.id) if self.type == 'ticket' else self.id
        return '%s (on %s)' % (self.filename, attached_to)
