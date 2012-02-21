====================================
Генерируем внешние API по-питоновски
====================================

В python есть негласное правило - никогда не повторяйся.
Чаще всего если в программе приходиться писать почти одно и то-же два раза, значит
вы что-то сделали не так. Я приведу пример, как можно 
автоматизировать генерацию внешних API таким образом, что 
достаточно будет в одном месте в удобной и универсальной форме 
описать поддерживаемые вызовы, а все внешнее API для этих 
вызовов сделает написаный один раз код.

Итак мы пишем серверный компонент программы, который должен
контролироваться внешними утилитами. Типичные варианты управления:

* CLI - административный интерфейс командной строки, так-же удобен для разработки 
* REST - для других языков, WebUI & Co
* RCP в каком-то виде (thrift, PyRo, etc)

Нам нужна библиотека, которая позволит один раз задать интерфейсы API функций,
сгенерирует по ним интерфейсы для всех внешних API, будет автоматически 
проверять входящие параметры и сделает удобочитаемую документацию. 
Для начала хватит. 

.. cut::
    
    pass
    pass


Любая библиотека проектируется отталкиваясь от примеров ее использования.

.. sourcecode:: python

    class Add(APICallBase): 
        "Add two integers"
        class Params(object):
            params = Param([int], "list of integers to make a sum")

        def execute(self):
            return sum(self.params)


    class Sub(APICallBase):
        "Substitute two integers"
        class Params(object):
            params = Param((int, int), "substitute second int from first")

        def execute(self):
            return self.params[0] - self.params[1]


    class Ping(APICallBase):
        "Ping host"
        class Params(object):
            ip = Param(IPAddr, "ip addr to ping")
            num_pings = Param(int, "number of pings", default=3)

        def execute(self):
            res = subprocess.check_stdout('ping -c {0} {1}'.format(self.num_pings, 
                                                                     self.ip))
            return sum(map(float, re.findall(r'time=(\d+\.?\d*)', out))) / \
                                self.num_pings


Это желаемое описание API. Каждый API вызов наследует класс **APICallBase**, 
определяет внутренний класс **Params**, где экземплярами класса **Param** описывает
параметры вызова и перегружает вызов **execute**, в котором выполняется вся работа.
Этой информации более чем достаточно, что-бы сгенерировать все API 
и документацию пользуясь интроспекцией и генерацией объектов на лету.

Начнем с базы - нужно уметь находить все классы, унаследованные от **APICallBase**.
Это можно сделать через метаклассы_

.. sourcecode:: python.hide

    class APIMeta(type):

        # список всех API вызовов
        api_classes = []
        def __new__(cls, name, bases, clsdict):

            new_cls = super(APIMeta, cls).__new__(cls, name, bases, clsdict)
            
            # пропускаем APICallBase
            if name != 'APICallBase':
                self.api_classes.append(new_cls)
                
                # all_params итерирует по всем параметрам этого вызова
                # передаем в параметры имена атрибутов, которым они присвоены
                # таким образом мы избегаем дублирования имени 'ip' в след строке
                # ip = Param(IPAddr, "ip addr to ping")
                # и других таких-же

                for name, param in new_cls.Params.__dict__.items():
                    param.name = name

            return new_cls

    # базовый класс для всех API вызовов
    class APICallBase(object):
        __metaclass__ = APIMeta
    
        def __init__(self, **dt):
            self._consume(dt)

        @classmethod
        def name(cls):
            return cls.__name__.lower()

        @classmethod
        def all_params(cls):
            return cls.Params.__dict__.values()

        def rest_url(self):
            return '/{0}'.format(self.name())

        @classmethod
        def from_dict(cls, data):
            obj = cls.__new__(cls)
            obj._consume(data)
            return obj

        def _consume(self, data, from_strings=False):
            # этот метод заполняет экземпляр команды из словаря параметров
            # и проводит все необходимые проверки параметров

            
            required_param_names = set()
            all_param_names = set()

            for param in self.all_params():
                if param.required():
                    required_param_names.add(param.name)
                all_param_names.add(param.name)

            # проверяем наличие лишних параметров data
            extra_params = set(data.keys()) - all_param_names
            if extra_params != set():
                raise ValueError("Extra parameters {0} for cmd {1}".format(
                                 ','.join(extra_params), self.__class__.__name__))

            # проверяем наличие в data всех необходимых параметров
            missed_params = required_param_names - set(data.keys())
            if missed_params != set():
                raise ValueError("Missed parameters {0} for cmd {1}".format(
                                 ','.join(missed_params), self.__class__.__name__))

            # проверяем значение параметра или пребразовываем его из строки
            # (прошедшей из CLI) в целевой тип

            parsed_data = {}
            for param in self.all_params():
                try:
                    val = data[param.name]
                except KeyError:
                    parsed_data[param.name] = param.default

                if from_strings:
                    parsed_data[param.name] = param.from_cli(val)
                else:
                    param.validate(val)
                    parsed_data[param.name] = val

            # обновляем аттрибуты и возвращает объект
            self.__dict__.update(parsed_data)
            return self

        def to_dict(self):
            res = {}
            for param in self.all_params():
                res[param.name] = getattr(self,  param.name)
            return res

        def execute(self):
            # базовый метод для выполнения работы
            pass

        def __str__(self):
            res = "{0}({{0}})".format(self.__class__.__name__)
            params = ["{0}={1!r}".format(param.name, getattr(self, param.name))
                            for param in self.all_params()]
            return res.format(', '.join(params))

        def __repr__(self):
            return str(self)


Классы для типов данных, используемых в **Params**

.. sourcecode:: python

    # базовый класс для типов данных
    class DataType(object):
        
        # проверить, про val принадлежит к денному типу
        def validate(self, val):
            return True

        # преобразовать val из формата для командной строки
        def from_cli(self, val):
            return None

        # параметры для парсера CLI
        def arg_parser_opts(self):
            return {}

    # список параметров определенного типа
    class ListType(DataType):
        def __init__(self, dtype):
            self.dtype = get_data_type(dtype)

        def validate(self, val):
            if not isinstance(val, (list, tuple)):
                return False

            for curr_item in val:
                if not self.dtype.valid(curr_item):
                    return False
            
            return True

        def from_cli(self, val):
            return [self.dtype.from_cli(curr_item) for curr_item in val]

        def arg_parser_opts(self):
            opts = self.dtype.arg_parser_opts()
            opts['nargs'] = '*'
            return opts

    # целое число
    class IntType(DataType):
        
        def validate(self, val):
            return isinstance(val, int)

        def from_cli(self, val):
            return int(val)

        def arg_parser_opts(self):
            return {'type': int}

Итак переходим к генерации API. Для начала - CLI

.. sourcecode:: python

    def get_arg_parser():
        parser = argparse.ArgumentParser()
        subparsers = parser.add_subparsers()

        for call in APIMeta.api_classes():

            # для каждого вызова - свой вложенный парсер
            sub_parser = subparsers.add_parser(call.name(), 
                                               help=call.__doc__)
            sub_parser.set_defaults(cmd_class=call)
            
            # проходим по всем параметрам и добавляем для них опции в CLI
            for param in call.all_params():
                opts = {'help':param.help}

                # значение по умолчанию, если оно есть
                # _NoDef это специальный класс, что-бы отличать значение
                # None и полное отсутствие параметра
                if param.default is not _NoDef:
                    opts['default'] = param.default
                
                opts.update(param.arg_parser_opts())
                sub_parser.add_argument('--' + param.name.replace('_', '-'),
                                    **opts)
        return parser, subparsers


REST API с помощью CherryPy_

.. sourcecode:: python

    import cherrypy as cp
    def get_cherrypy_server():
        
        class Server(object):
            pass

        # замыкание-обработчик для команды

        def call_me(cmd_class):

            # обмениваться данными будем через json
            @cp.tools.json_out()
            def do_call(self, opts):
                cmd = cmd_class.from_dict(json.loads(opts))
                return cmd.execute()
            return do_call

        # добавляем к классу Server по методу для каждой команды
        # CherryPy будет их вызывать для обработки REST запросов

        for call in APIMeta.all_classes(APICallBase):
            setattr(Server, 
                    call.name(), 
                    cp.expose(call_me(call)))

        return Server

CherryPy довольно интересный веб-сервер, который использует интроспекцию 
и атрибуты классов для обработки HTTP запросов. Запрос вида 
http://localhost:8080/xyz?a=1&b=2 приведет к вызову **Server.xyz(a="1", b="2")**,
если такой есть и проброшен в web через **cherrypy.expose**.

Завершающий аккорд - функция main

.. sourcecode:: python

    def main(argv=None):

        # наполняем парсер CLI и разбираем командную строку
        argv = argv if argv is not None else sys.argv
        parser, subparsers = get_arg_parser()

        sub_parser = subparsers.add_parser('start-server', 
                                            help="Start REST server")
        sub_parser.set_defaults(cmd_class='start-server')

        res = parser.parse_args(argv)
        cmd_cls = res.cmd_class

        # если пришел запрос на запуск сервера
        if cmd_cls == 'start-server':
            rest_server = get_cherrypy_server()
            cp.quickstart(rest_server())
        else:
            # иначе конструируем объек-команду
            for opt in cmd_cls.all_params():
                data = {}
                try:
                    data[opt.name] = getattr(res, opt.name.replace('_', '-'))
                except AttributeError:
                    pass
            cmd = cmd_cls.from_dict(data)

            # если не определена переменная окружения REST_SERVER_URL
            rest_url = os.environ.get('REST_SERVER_URL', None)

            if rest_url is None:
                # исполняем локально
                print "Local exec"
                print "Res =", cmd.execute()
            else:
                # иначе исполняем на сервере
                print "Remote exec"
                params = urllib.urlencode({'opts': json.dumps(cmd.to_dict())})
                res = urllib2.urlopen("http://{0}{1}?{2}".format(rest_url, 
                                                                 cmd.rest_url(),
                                                                 params)).read()
                print "Res =", json.loads(res)


        return 0

Пробуем:

.. sourcecode:: console

    $ python api.py -h
    usage: api.py [-h] {add,sub,ping,start-server} ...

    positional arguments:
      {add,sub,ping,start-server}
        add                 Add two integers
        sub                 Substitute two integers
        ping                Ping host
        start-server        Start REST server

    optional arguments:
      -h, --help            show this help message and exit

    $ python api.py add --params 1 3 
    Local exec
    Res = 4

    $ export REST_SERVER_URL=localhost:8080

    $ python api.py add --params 1 3 
    Remote exec
    Res = 4

Идея очень простая, так что особенно писать нечего - код говорит сам за себя.
Более полный вариант можно найти на `koder github`_. Основная мысль - вынос каждой команды
в отдельный класс и описание всех ее параметров в виде, удобном для интроспекции.
Похожим на описанный образом можно генерировать логику для `django piston`_,
html документацию по всем параметрам, отличия между версиями API для различных версий
сервера и другое, как это делается на нашем текущем проекте.


.. _метаклассы: http://koder-ua.blogspot.com/2011/12/blog-post.html
.. _CherryPy: http://tools.cherrypy.org/
.. _koder github: https://github.com/koder-ua/python-lectures/blob/master/posts/api.py
.. _django piston: https://bitbucket.org/jespern/django-piston/wiki/Home
