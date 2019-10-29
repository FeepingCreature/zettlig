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

class Trace:
    def __init__(self, file):
        self.file = file
        self.names = []
        self.read()

    def read(self):
        try:
            with open(self.file, 'r') as file:
                self.names = [name for name in file.read().splitlines() if len(name)]
        except FileNotFoundError:
            pass

    def write(self):
        with open(self.file, 'w') as file:
            file.write(self.names.join('\n'))

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

@app.route('/zettel/<name>/edit', methods=['POST'])
def edit(name):
    global root_path
    zettel = Zettel(name=name)
    zettel.write(content=request.form['content'])
    return redirect(root_path)

@app.route('/')
def index():
    zettels = load_zettels()
    trace = Trace("data/trace.txt")
    # names = trace.names
    names = sorted(zettels.keys())
    context = {
        'names': names,
        'zettels': [zettels[name] for name in names],
        'toggle': ToggleHack,
    }
    return render_template('index.html', **context)

if __name__ == "__main__":
    app.run()
