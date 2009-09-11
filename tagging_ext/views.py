"""
    Add this to your root urls_conf (urls.py)

    tagged_models = (
        dict(title="Blog Posts", 
            query=lambda tag : TaggedItem.objects.get_by_model(Post, tag).filter(status=2),
            custom_template="tagging_ext/default_template.html",
        ),
    )

    tagging_ext_kwargs = {
        'tagged_models':tagged_models,
        'default_template':'custom_templates/special.html'

    }
    
    urlpatterns += patterns('',
        url(r'^tags/(?P<tag>.+)/(?P<model>.+)$', 'tagging_ext.views.tag', kwargs=tagging_ext_kwargs, name='tagging_ext_tag'),
        url(r'^tags/(?P<tag>.+)$', 'tagging_ext.views.index', kwargs=tagging_ext_kwargs, name='tagging_ext_index'),    
    )    
"""

from django.core.exceptions import ObjectDoesNotExist
from django.db import connection
from django.http import Http404
from django.shortcuts import render_to_response, get_object_or_404
from django.template import RequestContext

from tagging.models import Tag # use these to check for tag content

from sys import stderr

def get_model_counts(tagged_models, tag):
    """ This does a model count so the side bar looks nice.
    """
    model_counts = []
    for model in tagged_models:
        model['count'] = model['query'](tag).count()
        model_counts.append(model)
                 
    return model_counts
    
def index(request, template_name="tagging_ext/index.html", min_size=0,limit=10):
    """
        min_size: Smallest size count accepted for a tag
        order_by: asc or desc by count
        limit: maximum number of tags to display 
        
        TODO: convert the hand-written query to an ORM call. Right now I know
                this works with Sqlite3 and PostGreSQL.
    """
    query = """
        SELECT tag_item.tag_id as tag_id, COUNT(tag_item.tag_id) as counter 
        FROM tagging_taggeditem as tag_item 
        GROUP BY tag_id
        HAVING COUNT(tag_item.tag_id) > %s
        ORDER BY counter desc
        LIMIT %s
    """  % (min_size, limit)

    cursor = connection.cursor()
    cursor.execute(query)
    
    results = []
    
    for row in cursor.fetchall():
        try:
            tag=Tag.objects.get(id=row[0])
        except ObjectDoesNotExist:
            continue
            
        if ' ' in tag.name:
            continue
        
        record = dict(
            tag=tag,
            count=row[1]
        )
        results.append(record)    
        
    dictionary = {
        'tags':results
    
    }
    

    return render_to_response(template_name, dictionary,
        context_instance=RequestContext(request))      
    

def tag(request, tag='', template_name="tagging_ext/tag.html", tagged_models=(), default_template=None):
    
    # does the tag actually exist?
    tag = get_object_or_404(Tag, name=tag)
            
    dictionary = { 
        'tag': tag,
        'model_counts': get_model_counts(tagged_models,tag)
    }
    
    return render_to_response(template_name, dictionary,
        context_instance=RequestContext(request))      

def tag_by_model(request, tag, model, template_name="tagging_ext/tag_by_model.html", tagged_models=(),default_template='tagging_app/default_template.html'):

    # does the tag actually exist?    
    tag = get_object_or_404(Tag, name=tag)    
    
    model_counts = get_model_counts(tagged_models, tag)
    
    results = None
    for item in model_counts:             
        
        # If the model being displayed is the same as what is being looped          
        if model == item.get('title', ''):
            
            # Fetch the lambda function which runs the ORM query
            query = item.get('query', None)
            
            if query:
                
                # get the results
                results = query(tag)
                
                # And if there is a custom_template, use that.
                # otherwise use the default template
                content_template = item.get('custom_template',default_template)                
                break
    
    if not results:
        raise Http404('No available items to display for this tag.')
        

    
    dictionary = { 
        'tag': tag,
        'model': model,
        'model_counts': model_counts,
        'content_template': content_template,
        'results': results
    }
    
    return render_to_response(template_name, dictionary,
        context_instance=RequestContext(request))      
