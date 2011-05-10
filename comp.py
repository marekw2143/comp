#! /usr/bin/python

# author:   Marek Wawrzyczek
# e-mail:   mwawrzyczek@gmail.com
# www:      http://marekw2143.livejournal.com

import sys
import os
import pdb


INPUT = 1
OUTPUT = 1
TO_TEMP = 2
def prn(s): print s


# it's assumed that all BM subclasses programs generate commands that can write to STDOUT
class BM(object): #BaseMethod
    def __init__(self, is_dir = False, verbose = False):
        self.is_dir = is_dir
        self.verbose = verbose
        self.next_module = None
        self.before_handlers = []
        self.after_handlers = []
    
    def accepts_stdin(self):
        """
        Informs whether method accepts input data from stdinput
        """
        return True

    def set_input(self, input):
        self.input = input
    
    def set_output(self, output):
        self.output = output

    def get_temp_file(self):
        pass
    
    def output_to_tempfile(self):
        temp_file_name = "GET_TEMP_FILE_NAME"
        self.output = temp_file_name

        #it shold be added to after list containing current object
        self.next_module.ext_list_container.after_handlers.append(lambda: prn('deleting ' + temp_file_name))
        self.next_module.input = self.output
        

    def set_self_output(self):
        global OUTPUT, TO_TEMP
        if self.output == OUTPUT:
            self.output = self.stdout
        else:
            if self.output == TO_TEMP:
                self.output_to_tempfile()
        self.ret.append(self.output)

    def set_self_input(self):
        if self.input == INPUT:
            self.input = self.stdin
        self.ret.append(self.input)
    

class ToolMeta(type):
    def __new__(cls, name, bases, attribs):
        def get_name_restr(name, value):
            return name.lower().startswith('co') and issubclass(value, BM)

        def dec_name_restr(name, value):
            return name.lower().startswith('de') and issubclass(value, BM)

        def add_comp_method(obj, name, method):
            setattr(obj, name, method)

        def check_method(name, name_filter):
            if not getattr(cls, name, None):
                if len([x for x in attribs if name_filter(x, attribs[x])]) == 1:
                    for key, val in attribs.iteritems():
                        if name_filter(key, val):
                            add_comp_method(ret, name, classmethod(lambda cls, name: val))
                            return
                else:
                    raise Exception("can't figure out " + name + " class")

        ret = super(ToolMeta, cls).__new__(cls, name, bases, attribs)

        # since Tool is an abstract class, we dont' need so that it has any methods
        if name == 'Tool':
            return ret

        check_method('get_compressor', get_name_restr)
        check_method('get_decompressor', dec_name_restr)
        return ret
        

class Tool(object):
    __metaclass__ = ToolMeta
    @classmethod
    def accepts(cls, name):
        return name in cls.extensions
        
class ZipTool(Tool):
    extensions = ['zip']

    class compress_zip(BM):
        stdin = stdout = '-'
        def __call__(self):
            global INPUT, OUTPUT, TO_TEMP
            self.ret = ['zip']

            self.set_self_output()
            self.set_self_input()

            if self.is_dir:
                self.ret.append('-r')

            return ' '.join(self.ret)

    class decompress(BM):
        stdout = '-c'
        def __call__(self):
            global INPUT, OUTPUT, TO_TEMP
            self.ret = ['unzip']
    
            # process output
            self.set_self_output()
        
            # process input
            if self.input == INPUT:
                raise Exception("This tool can't read from stdin")
            else:
                self.ret.append(self.input)

            return ' '.join(self.ret)

        def accepts_stdin(self):
            return False

class TarTool(Tool):
    extensions = ['tar']

    class compress_tar(BM):
        stdin = stdout = '-'
        def __call__(self):
            global INPUT, OUTPUT, TO_TEMP

            self.ret = ['tar']

            # build options
            opts = ['c']
            if self.verbose: opts.append('vv')
            opts.append('f')
            self.ret.append('-' + ''.join(opts))
            self.set_self_output()
            self.set_self_input()

            return ' '.join(self.ret)
    class decompress_tar(BM):
        stdin = stdout = '-'
        def __call__(self):
            global INPUT, OUTPUT, TO_TEMP

            self.ret = ['tar']

            # build options
            opts = ['x']
            if self.verbose: opts.append('vv')
            opts.append('f')
            self.ret.append('-' + ''.join(opts))

            self.set_self_output()
            self.set_self_input()
            return ' '.join(self.ret)

class Bz2Tool(Tool):
    extensions = ['bz2', 'bz', 'tbz', 'tbz2']

    class compress(BM):
        stdout = '-c'
        def __call__(self):
            global INPUT, OUTPUT, TO_TEMP
            to_specified_file = False

            self.ret = ['bzip2']

            # if other tool want's to read from file, then that tool will be in next ExtList
            # so that it's save to do > here in ouptut
            if self.output == OUTPUT:                                       
                self.ret.append(self.stdout)
            else: 
                to_specified_file = True

            if self.input == INPUT:
                pass #if no input name then writes from input
            else:
                self.ret.append(self.input)
    
            if to_specified_file:
                self.ret.append('>' + self.output)
            else:
                if self.input == INPUT: 
                    self.ret.remove(self.stdout)

            return ' '.join(self.ret)

    class decompress_bz2(BM):
        stdout = '-c'
        def __call__(self):
            global INPUT, OUTPUT, TO_TEMP
            to_specified_file = False

            self.ret = ['bunzip2']
            if self.output == OUTPUT:
                self.ret.append(self.stdout)
            else: 
                to_specified_file = True

            if self.input == INPUT:
                pass #if no input name then writes from input
            else:
                self.ret.append(self.input)
    
            if to_specified_file:
                self.ret.append('>' + self.output)


            return ' '.join(self.ret)

class Manager(object):
    c_compressors = [ZipTool, TarTool, Bz2Tool]

    def get_compressor(self, name):
        """
        returns compressor class for proper extension
        """
        for cls in self.c_compressors:
            if cls.accepts(name):
                return cls.get_compressor(name)

    def get_decompressor(self, name):
        """
        returns decompressor class for proper extension
        """
        for cls in self.c_compressors:
            if cls.accepts(name):
                return cls.get_decompressor(name)

    def get_available(self):
        """
        returns available formats
        """
        ret = set()
        for comp in self.c_compressors:
            for x in comp.extensions:
                ret.add(x)
        return ret
        
        
class ExtList(list):
    def __init__(self, *args, **kwargs):
        list.__init__(self, *args, **kwargs)
        self.after_handlers = []

    def __get_command(self):
        cmd = '|'.join(map(lambda x: x(), self))
        return cmd

    def __execute_command(self, cmd):
        print 'executing: ' + str(cmd)

    def perform_operations(self):
        cmd = self.__get_command()
        self.__execute_command(cmd)
        for handler in self.after_handlers:
            handler()

    def append(self, obj):
        list.append(self, obj)
        setattr(obj, 'ext_list_container', self)
        

# TODO: add something like name extractor, which would detect that if extension is ['tbz2']
# then it will be changed to ['tbz2', 'tar'] so that program can be savely
class Base(object):
    "Base class for manager"
    mgr = Manager()

    def process_list(self, lst):
        cmd = '|'.join(map(lambda x: x(), lst))
        print cmd

    def available_formats(self):
        return self.mgr.get_available()
            
    def do_work(self, source, extensions, out_file = "OUT_FILE"):
        global INPUT, OUTPUT, TO_TEMP
        ext_list = self.get_ext_list(extensions)
        is_dir = os.path.isdir(source)

        allowed = self.mgr.get_available()
        init, prepared = [], [ExtList(),]

        for ext in ext_list:
            cmp = self.get_cmp_method(ext)()
            init.append(cmp)

        # configure first element
        init[0].set_input(source) #first item always read from file
        init[0].set_output(OUTPUT) #first item always read from file
        if is_dir: 
            init[0].is_dir = True

        prepared[0].append(init[0])
        for act, prev in zip(init[1:], init[:-1]):

            # below loop configures STDOUT of prev and STDI of act if act accepts STDIN
            
            #if act can't read from stdin - prev module should write to TEMP_FILE 
            #and inform act about that after writing to file
            #and act should be processed in separate process chain
            if not act.accepts_stdin(): 
                prepared.append(ExtList())
                prev.next_module = act
                prev.set_output(TO_TEMP)
            
            # if act can read from STDIN then previous writes to STDOUT and act reads from STDIN
            else:
                act.set_input(INPUT)
                prev.set_output(OUTPUT)
            prepared[-1].append(act)

        prepared[-1][-1].set_output(OUTPUT) # last item always wries to STDOUT
        prepared[-1].append(lambda: 'tee %s' % out_file)
        

        for lst in prepared:
            lst.perform_operations()

    def perform_action(self, args):
        raise NotImplementedYet

    def get_ext_list(self, extensions):
        return extensions.split(".")


class Compressor(Base):
    default_compression = 'tar.bz2'
    def __init__(self):
        self.get_cmp_method = self.mgr.get_compressor


    def perform_action(self, args):
        source = args[0]
        if source.endswith('/'): source = source[:-1]
        try:
            extensions = args[1]
        except:
            extensions = self.default_compression
        name = source + '.' +  extensions
        try:
            name = args[2]
        except:
            pass

        self.do_work(source, extensions, name)

class Decompressor(Base):
    def __init__(self):
        self.get_cmp_method = self.mgr.get_decompressor

    
    def perform_action(self, args):
        source = args[0]
        available = self.available_formats()

        splitted_source = source.split('.')
        extensions = []
        while splitted_source:
            fmt = splitted_source.pop()
            if fmt in available:
                extensions.append(fmt)
            else:
                break
        extensions = '.'.join(extensions)

        self.do_work(source, extensions)

def install():
    print 'installing'

if __name__ == '__main__':
    install_mode = None
    try:
        if sys.argv[1] =='install':
            install_mode = True
            install()
    except:
        pass

    if not install_mode:
        # choosing work mode on the basis of executed program name
        # TODO: use regex instead
        start_name = sys.argv[0]
        start_map = {
            Compressor: ['co', 'comp.py'],
            Decompressor: ['de'],
        }
        for cls, names in start_map.iteritems():
            for name in names:
                if start_name.find(name) >= 0:
                    perf = cls()
                    break
        perf.perform_action(sys.argv[1:])
