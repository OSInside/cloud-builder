#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Cloud Builder documentation build configuration file
#
import sys
from os.path import abspath, dirname, join, normpath
import shlex
import sphinx_rtd_theme

# -- Paths ------------------------------------------------
# If extensions (or modules to document with autodoc) are in another directory,
# add these directories to sys.path here. If the directory is relative to the
# documentation root, use os.path.abspath to make it absolute, like shown here.
_path = normpath(join(dirname(__file__), "../.."))
sys.path.insert(0, _path)


# -- General configuration --------------------------------
# Add any Sphinx extension module names here, as strings. They can be
# extensions coming with Sphinx (named 'sphinx.ext.*') or your custom
# ones.

extensions = [
    'sphinx.ext.autodoc',
    'sphinx.ext.autosummary',
    'sphinx.ext.extlinks',
    'sphinx.ext.todo',
    'sphinx.ext.ifconfig',
    'sphinx.ext.viewcode',
    'sphinx.ext.autodoc',
    'sphinx.ext.intersphinx',
]

def remove_module_docstring(app, what, name, obj, options, lines):
    if what == "module" and name in docopt_ignore:
        del lines[:]

def prologReplace(app, docname, source):
    result = source[0]
    for key in app.config.prolog_replacements:
        result = result.replace(key, app.config.prolog_replacements[key])
    source[0] = result

def setup(app):
    app.add_config_value('prolog_replacements', {}, True)
    app.connect('source-read', prologReplace)
    app.connect("autodoc-process-docstring", remove_module_docstring)
    app.add_css_file('css/custom.css')


prolog_replacements = {
    '{CB}': 'Cloud Builder'
}

latex_documents = [
    (
        'index',
        'cloud_builder.tex',
        'Cloud Builder Documentation',
        'Marcus Schäfer',
        'manual'
    )
]
latex_elements = {
    'papersize': 'a4paper',
    'pointsize':'12pt',
    'classoptions': ',openany',
    'babel': '\\usepackage[english]{babel}',
    'preamble': r'''
      \makeatletter
      \fancypagestyle{normal}{
        \fancyhf{}
        \fancyfoot[LE,RO]{{\py@HeaderFamily\thepage}}
        \fancyfoot[LO]{{\py@HeaderFamily\nouppercase{\rightmark}}}
        \fancyfoot[RE]{{\py@HeaderFamily\nouppercase{\leftmark}}}
        \fancyhead[LE,RO]{{\py@HeaderFamily \@title, \py@release}}
        \renewcommand{\headrulewidth}{0.4pt}
        \renewcommand{\footrulewidth}{0.4pt}
      }
      \makeatother
    '''
}

# Add any paths that contain templates here, relative to this directory.
templates_path = ['.templates']

# The suffix(es) of source filenames.
# You can specify multiple suffix as a list of string:
# source_suffix = ['.rst', '.md']
source_suffix = '.rst'

# The encoding of source files.
source_encoding = 'utf-8-sig'

# The master toctree document.
master_doc = 'index'

default_role="py:obj"

# General information about the project.
project = 'Cloud Builder'
copyright = '2021, Marcus Schäfer'
author = 'Marcus Schäfer'

# The version info for the project you're documenting, acts as replacement for
# |version| and |release|, also used in various other places throughout the
# built documents.
#
# The short X.Y version.
version = '0.2.32'
# The full version, including alpha/beta/rc tags.
release = version

# The language for content autogenerated by Sphinx. Refer to documentation
# for a list of supported languages.
#
# This is also used if you do content translation via gettext catalogs.
# Usually you set "language" from the command line for these cases.
language = 'en'

# List of patterns, relative to source directory, that match files and
# directories to ignore when looking for source files.
exclude_patterns = []

# If true, '()' will be appended to :func: etc. cross-reference text.
#add_function_parentheses = True

# If true, the current module name will be prepended to all description
# unit titles (such as .. function::).
#add_module_names = True

# If true, sectionauthor and moduleauthor directives will be shown in the
# output. They are ignored by default.
#show_authors = False

# The name of the Pygments (syntax highlighting) style to use.
pygments_style = 'sphinx'

# A list of ignored prefixes for module index sorting.
#modindex_common_prefix = []

# If true, keep warnings as "system message" paragraphs in the built documents.
#keep_warnings = False

# If true, `todo` and `todoList` produce output, else they produce nothing.
todo_include_todos = True

extlinks = {
    'issue': ('https://github.com/OSInside/cloud-builder/issues/%s', '#'),
    'pr': ('https://github.com/OSInside/cloud-builder/pull/%s', 'PR #'),
    'ghkiwi': ('https://github.com/OSInside/cloud-builder/blob/master/%s', '')
}

autosummary_generate = True

# -- Options for HTML output ----------------------------------------------

#html_short_title = '%s-%s' % (project, version)
#html_last_updated_fmt = '%b %d, %Y'
#html_split_index = True
#html_logo = '.images/cloud-builder.logo.png'

html_sidebars = {
   '**': [
          'localtoc.html', 'relations.html',
          'about.html', 'searchbox.html',
         ]
}

html_theme = "sphinx_rtd_theme"

html_theme_path = [sphinx_rtd_theme.get_html_theme_path()]

html_static_path = ['.static']

html_theme_options = {
    'collapse_navigation': False,
    'display_version': False
}

# -- Options for manual page output ---------------------------------------

# The man page toctree documents.
cb_fetch_doc = 'commands/cb_fetch'
cb_prepare_doc = 'commands/cb_prepare'
cb_run_doc = 'commands/cb_run'
cb_scheduler_doc = 'commands/cb_scheduler'

# One entry per manual page. List of tuples
# (source start file, name, description, authors, manual section).
man_pages = [
    (
        cb_fetch_doc,
        'CB::fetch',
        'Project git update and rebuild service',
        [author],
        8
    ),
    (
        cb_prepare_doc,
        'CB::prepare',
        'Prepare buildroot environment service',
        [author],
        8
    ),
    (
        cb_run_doc,
        'CB::run',
        'Build package service',
        [author],
        8
    ),
    (
        cb_scheduler_doc,
        'CB::scheduler',
        'Manage package build requests service',
        [author],
        8
    )
]

intersphinx_mapping = {'python': ('https://docs.python.org/3', None)}

# If true, show URL addresses after external links.
#man_show_urls = False
