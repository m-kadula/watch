from pathlib import Path
import datetime as dt
import argparse

import prettytable as pt

from .connector import WatchDB, NullWatchError, QueryError
from .log import Record
from .interpolation.collection import LinearInterpolation


def smart_prompt(wait=10, add=0):
    """Returns the next instance where seconds are //wait as a datetime obj"""
    time = dt.datetime.now() + dt.timedelta(seconds=add)
    nex = dt.timedelta(seconds=wait + (time.second // wait * wait + wait) - time.second)
    return (time + nex).replace(microsecond=0)


def smart_measure(prompt, datetime):
    """Returns the difference between prompt and datetime"""
    return (prompt - datetime).total_seconds()


def smart_cycle(wait=10, add=0):
    """Returns time difference between the system watch and another watch"""
    prompt = smart_prompt(wait, add)
    input(f'press ENTER at {prompt.time()} ')
    return round(smart_measure(prompt, dt.datetime.now()), 1)


def shorten_list(initial_list):
    if len(initial_list) == 0:
        return "Null"

    out = []
    left = initial_list[0]
    right = initial_list[0]

    for i in range(1, len(initial_list)):

        if initial_list[i] - 1 == right:
            right = initial_list[i]
        else:
            if left == right:
                out.append(str(left))
            else:
                out.append(f"{left}-{right}")

            left = initial_list[i]
            right = initial_list[i]

    if left == right:
        out.append(str(left))
    else:
        out.append(f"{left}-{right}")

    return ', '.join(out)


def check_settings_table(db: WatchDB):
    tmp = db.con.execute("""SELECT name FROM sqlite_master WHERE type='table'
                            AND name='db_settings'""").fetchall()
    if not tmp:
        db.con.execute('CREATE TABLE db_settings (name VARCHAR(30) UNIQUE, value VARCHAR(30))')
    tmp = db.con.execute('SELECT * FROM db_settings WHERE name = ?', ("default_watch",))
    if len(tmp.fetchall()) == 0:
        db.con.execute('INSERT INTO db_settings VALUES (?, NULL)', ("default_watch",))
        db.con.commit()


def configure_default_watch(db: WatchDB, watch_id: int) -> None:
    check_settings_table(db)
    db.con.execute('UPDATE db_settings SET value = ? WHERE name = ?', (str(watch_id), "default_watch"))
    db.con.commit()


def get_default_watch(db: WatchDB) -> int | None:
    check_settings_table(db)
    tmp = db.con.execute("SELECT value FROM db_settings WHERE name = ?", ("default_watch",)).fetchall()
    if len(tmp) == 0 or tmp[0][0] is None:
        raise ValueError("No watch configured")
    return int(tmp[0][0])


def exec_command(database: WatchDB, inp: str):
    INTERPOLATION_METHOD = LinearInterpolation
    match inp.split():

        case ["change", "default", integer]:
            try:
                configure_default_watch(database, int(integer))
            except Exception as e:
                print(f"Could not change default due to error:\n{e}")
            else:
                print(f"default changed to {integer}")

        case ["watches"]:
            titles = ('watch id', 'name', 'date', 'cycles no.', 'measures no.')
            dat = database.database_info()
            table = pt.PrettyTable(titles)
            table.add_rows([(i.id, i.name, i.date_of_joining, len(i.cycles), i.total_number_of_measures)
                            for i in dat])
            print(table)

        case ["change", "watch", watch_id]:
            if watch_id.isnumeric():
                watch_id = int(watch_id)
                try:
                    database.change_watch(watch_id)
                except QueryError:
                    print(f'Error: watch {watch_id} does not exist')
                else:
                    print(f'Watch changed to {watch_id}')
            else:
                print("Error: watch id has to be an integer")

        case ["change", "cycle", cycle]:
            try:
                cycle = int(cycle)
                database.change_cycle(cycle)
            except QueryError:
                print(f'Error: cycle {cycle} does not exist')
            else:
                print(f'Cycle changed to {cycle}')

        case ["add", "watch", *name]:
            try:
                name = ' '.join(name)
                database.add_watch(name)
            except QueryError:
                print('Error: Unable to add watch')
            else:
                print(f'Added watch {name}')

        case ["new", "cycle"]:
            database.new_cycle()

        case ["measure"]:
            key = max(database.data.data, key=lambda x: x.time, default=Record(0.0, 0.0)).measure
            time = smart_cycle(add=key)
            inp = None
            while inp not in ['y', 'n']:
                inp = input(f'add measure {time}? [y/n] ')
            if inp == 'y':
                database.add_measure(time)
                print('Measure added')
            else:
                print('Measure not added')

        case ["manual", "measure", measure]:
            measure = round(float(measure), 1)
            database.add_measure(measure)

        case ["del", "watch"]:
            prompt = None
            while prompt not in ['y', 'n']:
                prompt = input(f'Delete watch {database.cur_watch_info().name}? [y/n] ')
            if prompt == 'y':
                try:
                    database.del_current_watch()
                except QueryError:
                    print('Error: Unable to delete watch')
                else:
                    print(f'watch deleted')

        case ["del", "cycle"]:
            prompt = None
            while prompt not in ['y', 'n']:
                prompt = input(f'Delete cycle {database.cycle}? [y/n] ')
            if prompt == 'y':
                try:
                    tmp = database.cycle
                    database.del_current_cycle()
                except QueryError:
                    print('Error: Unable to delete cycle')
                else:
                    print(f'cycle {tmp} deleted')

        case ["del", "measure", measure]:
            prompt = None
            while prompt not in ['y', 'n']:
                prompt = input(f'Delete measure {measure}? [y/n] ')
            if prompt == 'y':
                try:
                    database.del_measure(int(measure))
                except QueryError:
                    print(f'Error: Measure {measure} does not exist')
                else:
                    print(f'measure {measure} deleted')

        case ["log"]:
            data = database.data.get_log_with_dif()
            table = pt.PrettyTable(('log id', 'timedate', 'measure', 'difference'))
            table.add_rows([(log.other['id'], log.time, log.measure, log.other['difference'])
                           for log in data.data])
            print(str(table))

        case ["fill"]:
            data = database.data.fill(INTERPOLATION_METHOD).get_log_with_dif()
            table = pt.PrettyTable(('timedate', 'measure', 'difference'))
            table.add_rows([(log.time, log.measure, log.other['difference']) for log in data.data])
            print(str(table))

        case ["stat"]:
            data = database.data.fill(INTERPOLATION_METHOD)
            table = pt.PrettyTable(('average', 'deviation', 'delta'))
            try:
                table.add_row((data.average,
                               data.standard_deviation,
                               data.delta))
            except (ValueError, ZeroDivisionError):
                print("Could not produce stats.")
            else:
                print(str(table))

        case ["current"]:
            cycles = shorten_list(database.cur_watch_info().cycles)
            table = pt.PrettyTable(('watch id', 'name', 'current cycle', 'all cycles'))
            table.add_row((database.watch, database.cur_watch_info().name, database.cycle, cycles))
            print(str(table))

        case ["SQL"]:
            code = input('SQL> ')
            try:
                cursor = database.con.execute(code)
            except Exception as e:
                print(e)
            else:
                data = cursor.fetchall()
                if data:
                    table = pt.PrettyTable()
                    table.add_rows(data)
                    print(table)

        case ["exit"]:
            database.close()
            exit(0)

        case []:
            pass

        case _:
            print("Error: Invalid input")


def main():
    parser = argparse.ArgumentParser("Watch DB")
    parser.add_argument("--database", type=Path, default=Path('~').expanduser() / '.watchdb')
    args = parser.parse_args()

    database = WatchDB(str(args.database))

    print("watchDB - watch measurement database")

    try:
        default_watch = get_default_watch(database)
        database.change_watch(default_watch)
    except (IndexError, ValueError):
        print("Default watch is not configured.")

    while True:
        try:
            prompt = database.cur_watch_info().name
        except NullWatchError:
            prompt = ""
        inp = input(f"{prompt}> ")
        try:
            exec_command(database, inp)
        except NullWatchError:
            print("watch is null")


if __name__ == "__main__":
    main()
