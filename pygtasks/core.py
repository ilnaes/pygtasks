from queue import Queue
import re
import datetime
from .tui import Terminal
from .service import Connection


class PygTasks:
    def __init__(self, cred_json=None):

        self.alive = True
        self.q = Queue()
        self.connexion = Connection(self.q, cred_json)
        self.terminal = Terminal(self.q)
        self.cursor = 0

        self.connexion.get_lists()
        self.terminal.loop()

        self.lists = []

    def get_list(self):
        """ Gets the tasklist that the cursor is in """

        i = 0
        for x in self.lists:
            _, _, tasks = x
            N = len(tasks) if tasks else 0
            if self.cursor >= i and self.cursor < i + N + 1:
                return x

            i += N + 1

    def add_list(self):
        m = None
        while not m:
            m = self.terminal.get_prompt("Input list title: ", self.q)
            if m is None:
                return

        res = self.connexion.add_list({'title': m})
        self.lists.append([m, res, None])
        self.terminal.set_text(self.parse_state())

    def add_task(self):
        task = {}

        # could be streamlined
        m = None
        while not m:
            m = self.terminal.get_prompt("Input task title: ", self.q)
            if m is None:
                return
        task['title'] = m

        m = None
        while m is None:
            a = self.terminal.get_prompt("Input date (MM/DD/YYYY): ", self.q)
            if a is None:
                return

            m = re.search(r'^([0-9]{1,2})/([0-9]{1,2})/([0-9]{4})$', a)
            try:
                ts = datetime.datetime(int(m.group(3)), int(m.group(1)),
                                       int(m.group(2)))
            except:
                m = None

        m = None
        while m is None:
            m = self.terminal.get_prompt(
                "(Optional) Input time (HH:MM am/pm): ", self.q)
            if m is None:
                return

            if m != '':
                m = re.search(
                    r'^(0[0-9]|1[0-9]|2[0-3]|[0-9]):([0-5][0-9])\s*(AM|am|PM|pm)$',
                    m)
                try:
                    hours = int(
                        m.group(1)) + (0 if m.group(3) in ['AM', 'am'] else 12)
                    ts += datetime.timedelta(hours=hours,
                                             minutes=int(m.group(2)))
                except:
                    m = None

        task['due'] = ts.isoformat() + '.000Z'

        m = self.terminal.get_prompt("(Optional) Input notes: ", self.q)
        if m is None:
            return
        task['notes'] = m

        res = self.connexion.add_task(self.get_list()[1], task)
        for _, id, l in self.lists:
            if id == self.get_list()[1]:
                if l is not None:
                    l.append([task['title'], res, ts])
                    l.sort(key=(lambda x: x[2]))
                    self.terminal.set_text(self.parse_state())
                break

    def parse_state(self):
        res = []
        now = datetime.datetime.now()

        for ltitle, _, l in self.lists:
            if l is None:
                res.append('+ ' + ltitle)
            else:
                res.append('- ' + ltitle)
                for ttitle, _, dt in l:
                    dfmt = dt.strftime('%m/%d/%Y')

                    if dt < now:
                        line = u'  \033[31m{0} -- {1}\033[0m'.format(
                            dfmt, ttitle)
                    else:
                        line = u'  \033[32m{0} -- {1}\033[0m'.format(
                            dfmt, ttitle)

                    res.append(line)
                    # res.append('  ' + y)

        return res

    def scroll_cursor(self, n):
        if self.cursor + n >= 0 and self.cursor + n < self.get_length():
            self.cursor += n
            self.terminal.scroll_cursor(n)

    def delete(self):
        nottask, tasklist = self.get_item()
        if not nottask:
            self.remove_task(False)
        else:
            name, listid, _ = tasklist

            m = None
            while not m:
                m = self.terminal.get_prompt(
                    'Are you sure you want to delete ' + name + ' (y/n)? ',
                    self.q)
                if m is None:
                    return
                if m not in 'yYnN':
                    m = None

            text = self.parse_state()
            text[self.cursor] += ' ✗'
            self.terminal.set_text(text)

            self.connexion.remove_list(listid)
            for i in range(len(self.lists)):
                _, id, _ = self.lists[i]
                if id == listid:
                    del self.lists[i]
                    break

            if len(self.parse_state()) <= self.cursor:
                self.scroll_cursor(-1)
            self.terminal.set_text(self.parse_state())

    def remove_task(self, complete):
        nottask, task = self.get_item()

        if not nottask:
            text = self.parse_state()
            text[self.cursor] += ' ✓' if complete else ' ✗'
            self.terminal.set_text(text)

            tasklist = self.get_list()
            _, id, _ = task
            self.connexion.remove_task(tasklist[1], id, complete)

            for i in range(len(tasklist[2])):
                if tasklist[2][i][1] == id:
                    del tasklist[2][i]
                    break

            if len(self.parse_state()) <= self.cursor:
                self.scroll_cursor(-1)
            self.terminal.set_text(self.parse_state())

    def get_item(self):
        i = 0
        for l in self.lists:
            if self.cursor == i:
                return True, l

            i += 1
            _, _, desc = l
            if desc is not None:
                for task in desc:
                    if self.cursor == i:
                        return False, task
                    i += 1

    def get_length(self):
        res = len(self.lists)
        for _, _, l in self.lists:
            res += 0 if l is None else len(l)
        return res

    def toggle_list(self):
        task, item = self.get_item()

        if task:
            if item[2] is None:
                self.connexion.get_tasks(item[1])
            else:
                item[2] = None
                self.terminal.set_text(self.parse_state())
        else:
            self.terminal.input = item[0]
            self.terminal.refresh(False)

    def process_events(self, event):
        e, v = event
        if e == 'LISTS':
            self.lists = v
            self.terminal.set_text(self.parse_state())
        elif e == 'TASKS':
            for l in self.lists:
                if l[1] == v[0]:
                    l[2] = v[1]
            self.terminal.set_text(self.parse_state())
        elif e == Terminal.KEYPRESS:
            if v == 3 or v == 113:
                self.alive = False
                self.terminal.kill()
            elif v == 106:
                self.scroll_cursor(1)
            elif v == 107:
                self.scroll_cursor(-1)
            elif v == 32:
                self.toggle_list()
            elif v == 116:
                self.add_task()
            elif v == 108:
                self.add_list()
            elif v == 99:
                self.remove_task(True)
            elif v == 120:
                self.delete()
            # else:
            #     self.terminal.refresh()
            # self.terminal.set_input(str(v))

    def run(self):
        while self.alive:
            self.process_events(self.q.get())
