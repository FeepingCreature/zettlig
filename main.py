from enum import Enum
import os
from os import path

from flask import Flask, render_template, redirect, request
from flask_bootstrap import Bootstrap
from flaskext.markdown import Markdown

app = Flask(__name__)
root_path = '/zettlig/'
Bootstrap(app)
Markdown(app)

class AlternatingPair:
    def __init__(self, alphas='', digits=''):
        self.alphas = list(alphas)
        self.digits = list(digits)

    def string(self):
        return ''.join(self.alphas) + ''.join(self.digits)

    def increment(self):
        if self.digits:
            for i, digit in reversed(list(enumerate(self.digits))):
                if not digit == '9':
                    self.digits[i] = chr(ord(digit) + 1)
                    break
                else:
                    self.digits[i] = '0'
                    # overflow
            else:
                self.digits.append('0')
        else:
            for i, alpha in reversed(list(enumerate(self.alphas))):
                if not alpha == 'z':
                    self.alphas[i] = chr(ord(alpha) + 1)
                    break
                else:
                    self.alphas[i] = 'a'
                    # overflow
            else:
                self.alphas.append('a')

    def list(self):
        if self.digits:
            return [''.join(self.alphas), ''.join(self.digits)]
        return [''.join(self.alphas)]

    def depth(self):
        if self.digits:
            return 2
        return 1

class AlternatingPairs:
    def __init__(self, string=''):
        self.pairs = []

        for letter in string:
            if letter.isdigit():
                self.add_number(letter)
            else:
                self.add_alpha(letter)

    def add_number(self, digit):
        assert(digit >= '1' or digit <= '9')
        self.pairs[-1].digits.append(digit)

    def add_alpha(self, letter):
        assert(letter >= 'a' or letter <= 'z')
        if not self.pairs or self.pairs[-1].digits:
            self.pairs.append(AlternatingPair())
        self.pairs[-1].alphas.append(letter)

    def string(self):
        return ''.join(pair.string() for pair in self.pairs)

    def deepen(self):
        if not self.pairs or self.pairs[-1].digits:
            self.pairs.append(AlternatingPair('a'))
        else:
            self.pairs[-1].digits = list('1')

    def increment(self):
        self.pairs[-1].increment()

    def list(self):
        return [item for pair in self.pairs for item in pair.list()]

    def depth(self):
        return sum(pair.depth() for pair in self.pairs)

class Zettel:
    base = u'data/zettel'

    def __init__(self, name=None, file=None):
        assert(bool(name) != bool(file))

        if name:
            self.file = path.join(Zettel.base, '{}.md'.format(name))
            self.name = name
        else:
            self.file = file
            self.name = path.splitext(path.basename(file))[0]

    def next_name(self):
        pairs = AlternatingPairs(self.name)
        pairs.deepen()
        while Zettel(name=pairs.string()).exists():
            pairs.increment()
        return pairs.string()

    def indent(self):
        pairs = AlternatingPairs(self.name)
        return pairs.depth()

    def read(self):
        try:
            with open(self.file, 'r') as file:
                return file.read()
        except FileNotFoundError:
            pass

    def write(self, content):
        with open(self.file, 'w') as file:
            file.write(content)

    def exists(self):
        return path.exists(self.file)

    def preview(self):
        return self.read().split("\n")[0]

class Trace:
    def __init__(self, file = u'data/trace.txt'):
        self.file = file
        self.names = []
        self.read()

    def read(self):
        try:
            with open(self.file, 'r') as file:
                self.names = [name for name in file.read().splitlines() if len(name)]
        except FileNotFoundError:
            pass

    def insert(self, after, name):
        index = self.names.index(after)
        self.names.insert(index + 1, name)

    def append(self, new_name):
        self.remove(new_name)
        self.names.append(new_name)

    def remove(self, remove_name):
        self.names = [name for name in self.names if not name == remove_name]

    def write(self):
        with open(self.file, 'w') as file:
            file.write('\n'.join(self.names))

class ToggleHack:
    @staticmethod
    def id(zettel):
        return 'zettel-{}-toggle'.format(zettel.name)

    @staticmethod
    def reply(zettel):
        return 'zettel-{}-reply'.format(zettel.name)

def load_zettels():
    filelist = [path.join(Zettel.base, file)
                for root, dirs, files in os.walk(Zettel.base)
                for file in files]
    return {zettel.name: zettel for zettel in [Zettel(file=file) for file in filelist]}

class GraphicalTreeNode:
    def __init__(self, zettel, states):
        self.zettel = zettel
        self.states = states
        self.name = self.zettel.name

    def indentmarker(self):
        def marker(state):
            if state == TreeState.SINGLE:
                return '─'
            if state == TreeState.FIRST:
                return '┬'
            if state == TreeState.LAST:
                return '└'
            if state == TreeState.NONE:
                return '&nbsp;'
            if state == TreeState.PASS:
                return '│'
            if state == TreeState.FORK:
                return '├'
            assert False

        return ''.join([marker(state) for state in self.states]) + ' '

class TreeState(Enum):
    SINGLE = 1
    FIRST = 2
    PASS = 3
    FORK = 4
    LAST = 5
    NONE = 6

class TreeNode:
    def __init__(self):
        self.zettel = None
        self.children = {}

    def list(self):
        children = [self.children[name] for name in sorted(self.children.keys())]

        childlist = []
        if self.zettel:
            childlist.insert(0, GraphicalTreeNode(self.zettel, []))

        for i, child in enumerate(children):
            childlist += child.list()

        num_branches = sum(1 for child in childlist if child.states and (
            child.states[0] == TreeState.FIRST or child.states[0] == TreeState.SINGLE))
        branches = 0
        for i, child in enumerate(childlist):
            if num_branches and branches == num_branches:
                child.states.insert(0, TreeState.NONE)
            elif num_branches and child.states and (
                child.states[0] == TreeState.FIRST or child.states[0] == TreeState.SINGLE):
                branches += 1
                child.states.insert(0, TreeState.LAST if branches == num_branches else TreeState.FORK)
            elif len(childlist) == 1:
                child.states.insert(0, TreeState.SINGLE)
            elif i == 0:
                child.states.insert(0, TreeState.FIRST)
            elif i == len(childlist) - 1:
                child.states.insert(0, TreeState.LAST)
            else:
                child.states.insert(0, TreeState.PASS)

        return childlist

def tree_insert(tree, keys, zettel):
    if not tree:
        tree = TreeNode()

    try:
        key = next(keys)
    except StopIteration:
        tree.zettel = zettel
        return tree

    tree.children[key] = tree_insert(tree.children.get(key), keys, zettel)
    return tree

def prefix_sort(zettels):
    tree = None

    for name, zettel in zettels.items():
        keys = AlternatingPairs(name).list()

        tree = tree_insert(tree, iter(keys), zettel)
    return tree

@app.route('/zettel/<name>/edit', methods=['POST'])
def edit(name):
    global root_path
    zettel = Zettel(name=name)
    zettel.write(content=request.form['content'])
    return redirect(root_path)

@app.route('/zettel/<name>/insert/<next_name>', methods=['POST'])
def insert(name, next_name):
    global root_path
    zettel = Zettel(name=next_name)

    trace = Trace()
    trace.insert(after=name, name=next_name)
    trace.write()

    zettel.write(content=request.form['content'])
    return redirect(root_path)

@app.route('/trace/<name>/add', methods=['POST'])
def add_trace(name):
    global root_path
    trace = Trace()
    trace.append(name)
    trace.write()
    return redirect(root_path)

@app.route('/trace/<name>/remove', methods=['POST'])
def remove_trace(name):
    global root_path
    trace = Trace()
    trace.remove(name)
    trace.write()
    return redirect(root_path)

@app.route('/')
def index():
    zettels = load_zettels()
    trace = Trace()
    names = sorted(trace.names)

    zetteltree = prefix_sort(zettels).list()
    context = {
        'names': names,
        'zetteltree': zetteltree,
        'trace': [zettels[name] for name in names],
        'toggle': ToggleHack,
    }
    return render_template('index.html', **context)

if __name__ == "__main__":
    app.run()
