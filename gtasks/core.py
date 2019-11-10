from queue import Queue
import re
import datetime
from tui import Terminal
from api import Connection


class GTasks:
    def __init__(self):
        self.alive = True
        self.q = Queue()
        self.terminal = Terminal(self.q)
        self.connexion = Connection(self.q)
        self.cursor = 0

        self.connexion.get_lists()
        self.terminal.loop()

        self.state = []

    def get_list(self):
        i = 0
        for x in self.state:
            _, _, tasks = x
            N = len(tasks) if tasks else 0
            if self.cursor >= i and self.cursor < i + N + 1:
                return x

            i += N + 1

    def add_task(self):
        task = {}
        m = None
        while not m:
            m = self.terminal.get_prompt("Input title: ", self.q)
            if m is None:
                return
            task['title'] = m

        m = None
        while not m:
            a = self.terminal.get_prompt("Input date (MM/DD/YYYY): ", self.q)
            if a is None:
                return

            m = re.search(r'^([0-9]{1,2})/([0-9]{1,2})/([0-9]{4})$', a)
            try:
                ts = datetime.datetime(int(m.group(3)), int(m.group(1)), int(m.group(2)))
            except:
                m = None

        m = None
        while m is None:
            m = self.terminal.get_prompt("(Optional) Input time (HH:MM am/pm): ", self.q)
            if m is None:
                return

            if m != '':
                m = re.search(r'^(0[0-9]|1[0-9]|2[0-3]|[0-9]):([0-5][0-9])\s*(AM|am|PM|pm)$', m)
                try:
                    hours = int(m.group(1)) + (0 if m.group(3) in ['AM', 'am'] else 12)
                    ts += datetime.timedelta(hours=hours, minutes=int(m.group(2)))
                except:
                    m = None

        task['due'] = ts.isoformat() + '.000Z'

        m = None
        while m is None:
            m = self.terminal.get_prompt("(Optional) Input notes: ", self.q)
            if m is None:
                return
            task['notes'] = m

        res = self.connexion.add_task(self.get_list()[1], task)
        for _, x, l in self.state:
            if x == self.get_list()[1]:
                if l is not None:
                    l.append([task['title'], res, ts])
                    l.sort(key=(lambda x: x[2]))
                    self.terminal.set_text(self.parse_state())
                break

    def parse_state(self):
        res = []
        now = datetime.datetime.now()

        for t, _, l in self.state:
            if l is None:
                res.append('+ ' + t)
            else:
                res.append('- ' + t)
                for y, _, d in l:
                    dfmt = d.strftime('%m/%d/%Y')

                    if d < now:
                        line = u'  \033[31m{0} -- {1}\033[0m'.format(dfmt, y)
                    else:
                        line = u'  \033[32m{0} -- {1}\033[0m'.format(dfmt, y)

                    res.append(line)
                    # res.append('  ' + y)

        return res

    def scroll_cursor(self, n):
        if self.cursor + n >= 0 and self.cursor + n < self.get_length():
            self.cursor += n
            self.terminal.scroll_cursor(n)

    def complete_task(self):
        nottask, task = self.get_item()

        if not nottask:
            tasklist = self.get_list()
            _, x, _ = task
            self.connexion.complete_task(tasklist[1], x)

            for i in range(len(tasklist[2])):
                if tasklist[2][i][1] == x:
                    del tasklist[2][i]
                    break
            self.scroll_cursor(-1)
            self.terminal.set_text(self.parse_state())

    def get_item(self):
        i = 0
        for x in self.state:
            if self.cursor == i:
                return True, x

            i += 1
            _, _, desc = x
            if desc is not None:
                for y in desc:
                    if self.cursor == i:
                        return False, y
                    i += 1

    def get_length(self):
        res = len(self.state)
        for _, _, x in self.state:
            res += 0 if x is None else len(x)
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
            self.terminal.refresh()

    def process_events(self, event):
        e, v = event
        if e == 'LISTS':
            self.state = v
            self.terminal.set_text(self.parse_state())
        elif e == 'TASKS':
            for l in self.state:
                if l[1] == v[0]:
                    l[2] = v[1]
            self.terminal.set_text(self.parse_state())
        elif e == Terminal.KEYPRESS:
            if v == 3 or v == 113:
                self.alive = False
                self.terminal.kill()
            elif v == 10:
                self.scroll_cursor(1)
            elif v == 11:
                self.scroll_cursor(-1)
            elif v == 32:
                self.toggle_list()
            elif v == 97:
                self.add_task()
            elif v == 99:
                self.complete_task()
            else:
                self.terminal.text.append(str(v))
                self.terminal.refresh()
                # self.terminal.set_input(str(v))

    def run(self):
        while self.alive:
            self.process_events(self.q.get())


if __name__ == '__main__':
    app = GTasks()
    app.run()