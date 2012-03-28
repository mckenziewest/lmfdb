# -*- coding: utf-8 -*-
import math
from Lfunctionutilities import pair2complex, splitcoeff, seriescoeff
from sage.all import *
import sage.libs.lcalc.lcalc_Lfunction as lc
from sage.rings.rational import Rational
import re
import pymongo
import bson
import utils
from modular_forms.elliptic_modular_forms.backend.web_modforms import *
import time ### for printing the date on an lcalc file
import socket ### for printing the machine used to generate the lcalc file

logger = utils.make_logger("LF")

def get_attr_or_method(thiswillbeexecuted, attr_or_method_name):
    """
        Given an object O and a string "text", this returns O.text() or O.text depending on
        whether text is an attribute or a method of O itself _or one of its superclasses_, which I will
        only know at running time. I think I need an eval for that.   POD

    """
    # I don't see a way around using eval for what I want to be able to do
    # Because of inheritance, which method should be called depends on self
    try:
        return eval("thiswillbeexecuted."+attr_or_method_name)
    except:
        return None

def my_find_update(the_coll, search_dict, update_dict):
    """ This performs a search using search_dict, and updates each find in  
    the_coll using update_dict. If there are none, update_dict is actually inserted.
    """
    x = the_coll.find(search_dict,limit=1)
    if x.count() == 0:
        the_coll.insert(update_dict)
    else:
        for x in the_coll.find(search_dict):
            x.update(update_dict)
            the_coll.save(x)


def parse_complex_number(z):
    z_parsed = "(" + str(real_part(z)) + "," +str(imag_part(z)) + ")"
    return z_parsed

#############################################################################

def constructor_logger(object, args):
    logger.info(str(object.__class__)+str(args))
    #object.inject_database(["original_mathematical_object()", "poles", "residues", "kappa_fe",
    #    "lambda_fe", "mu_fe", "nu_fe"])  #Paul Dehaye put this here for debugging

class Lfunction:
    """Class representing a general L-function
    It can be called with a dictionary of these forms:

    dict = { 'Ltype': 'lcalcurl', 'url': ... }  url is any url for an lcalcfile
    dict = { 'Ltype': 'lcalcfile', 'filecontens': ... }  filecontens is the
           contents of an lcalcfile

    """

    def __init__(self, **args):
        constructor_logger(self,args)
        # Initialize some default values
        self.coefficient_period = 0
        self.poles = []
        self.residues = []
        self.kappa_fe = []
        self.lambda_fe =[]
        self.mu_fe = []
        self.nu_fe = []
        self.selfdual = False
        self.langlands = True
        self.texname = "L(s)"  # default name.  will be set later, for most L-functions
        self.texnamecompleteds = "\\Lambda(s)"  # default name.  will be set later, for most L-functions
        self.texnamecompleted1ms = "\\overline{\\Lambda(1-\\overline{s})}"  # default name.  will be set later, for most L-functions
        self.primitive = True # should be changed later
        self.citation = ''
        self.credit = ''

        # Initialize from an lcalcfile if it's not a subclass
        if 'Ltype' in args.keys():
            self._Ltype = args.pop("Ltype")
            # Put the args into the object dictionary
            self.__dict__.update(args)

            # Get the lcalcfile from the web
            if self._Ltype=='lcalcurl':
                if 'url' in args.keys():
                    try:
                        import urllib
                        self.filecontents = urllib.urlopen(self.url).read()
                    except:
                        raise Exception("Wasn't able to read the file at the url")
                else:
                    raise Exception("You forgot to supply an url.")

            # Parse the Lcalcfile
            self.parseLcalcfile()

            # Check if self dual
            self.checkselfdual()

            if self.selfdual:
                self.texnamecompleted1ms = "\\Lambda(1-s)"

            try:
                self.originalfile = re.match(".*/([^/]+)$", self.url)
                self.originalfile = self.originalfile.group(1)
                self.title = "An L-function generated by an Lcalc file: "+self.originalfile

            except:
                self.originalfile = ''
                self.title = "An L-function generated by an Lcalc file."

            self.generateSageLfunction()

    def Ltype(self):
        return self._Ltype

    def parseLcalcfile(self, filecontents):
        """ Extracts informtion from the lcalcfile
        """

        lines = filecontents.split('\n',6)
        self.coefficient_type = int(lines[0])
        self.quasidegree = int(lines[4])
        lines = self.lcalcfile.split('\n',8+2*self.quasidegree)
        self.Q_fe = float(lines[5+2*self.quasidegree])
        self.sign = pair2complex(lines[6+2*self.quasidegree])

        self.kappa_fe = []
        self.lambda_fe = []
        self.mu_fe = []
        self.nu_fe = []

        for i in range(self.quasidegree):
            localdegree = float(lines[5+2*i])
            self.kappa_fe.append(localdegree)
            locallambda = pair2complex(lines[6+2*i])
            self.lambda_fe.append(locallambda)
            if math.fabs(localdegree-0.5)<0.00001:
                self.mu_fe.append(2*locallambda)
            elif math.fabs(localdegree-1)<0.00001:
                self.nu_fe.append(locallambda)
            else:
                self.nu_fe.append(locallambda)
                self.langlands = False

        """ Do poles here later
        """

        self.degree = int(round(2*sum(self.kappa_fe)))

        self.level = int(round(math.pi**float(self.degree) * 4**len(self.nu_fe) * self.Q_fe**2 ))
        # note:  math.pi was not compatible with the sage type of degree

        self.dirichlet_coefficients = splitcoeff(lines[-1])


    def checkselfdual(self):
        """ Checks whether coefficients are real to determine
            whether L-function is selfdual
        """

        self.selfdual = True
        for n in range(1,min(8,len(self.dirichlet_coefficients))):
            if abs(imag_part(self.dirichlet_coefficients[n]/self.dirichlet_coefficients[0])) > 0.00001:
                self.selfdual = False

    def generateSageLfunction(self):
        """ Generate a SageLfunction to do computations
        """
        self.sageLfunction = lc.Lfunction_C(self.title, self.coefficient_type,
                                            self.dirichlet_coefficients,
                                            self.coefficient_period,
                                            self.Q_fe, self.sign ,
                                            self.kappa_fe, self.lambda_fe ,
                                            self.poles, self.residues)

    def createLcalcfile(self):
        thefile="";
        if self.selfdual:
            thefile += "2\n"  # 2 means real coefficients
        else:
            thefile += "3\n"  # 3 means complex coefficients

        thefile += "0\n"  # 0 means unknown type

        thefile += str(len(self.dirichlet_coefficients)) + "\n"  

        thefile += "0\n"  # assume the coefficients are not periodic

        thefile += str(self.quasidegree) + "\n"  # number of actual Gamma functions

        for n in range(0,self.quasidegree):
            thefile = thefile + str(self.kappa_fe[n]) + "\n"
            thefile = thefile + str(real_part(self.lambda_fe[n])) + " " + str(imag_part(self.lambda_fe[n])) + "\n"

        thefile += str(real_part(self.Q_fe)) +  "\n"

        thefile += str(real_part(self.sign)) + " " + str(imag_part(self.sign)) + "\n"

        thefile += str(len(self.poles)) + "\n"  # counts number of poles

        for n in range(0,len(self.poles)):
            thefile += str(real_part(self.poles[n])) + " " + str(imag_part(self.poles[n])) + "\n" #pole location
            thefile += str(real_part(self.residues[n])) + " " + str(imag_part(self.residues[n])) + "\n" #residue at pole

        for n in range(0,len(self.dirichlet_coefficients)):
            thefile += str(real_part(self.dirichlet_coefficients[n]))   # add real part of Dirichlet coefficient
            if not self.selfdual:  # if not selfdual
                thefile += " " + str(imag_part(self.dirichlet_coefficients[n]))   # add imaginary part of Dirichlet coefficient
            thefile += "\n"

        return(thefile)


############################################################################
### Returns the Lcalcfile, version 2
############################################################################

    def createLcalcfile_ver2(self, url):
        thefile=""
        thefile += "##########################################################################################################\n"
        thefile += "###\n"
        thefile += "### lcalc file for the url: " + url + "\n"
        thefile += "### This file assembled: " + time.asctime()  + "\n"
        thefile += "### on machine: " + socket.gethostname()  + "\n"
        thefile += "###\n"
        thefile += "##########################################################################################################\n\n"
        thefile += "lcalcfile_version = 2    ### lcalc files should have a version number for future enhancements\n\n"

        thefile += """\
##########################################################################################################
### Specify the functional equation using the Gamma_R and Gamma_C
### notation. Let Gamma_R = pi^(-s/2) Gamma(s/2), and  Gamma_C = (2 pi)^(-s) Gamma(s).
###
### Let Lambda(s) :=
###
###                  a
###               --------'
###              '  |  |
###          s      |  |
###   sqrt(N)       |  |   Gamma_{R or C}(s + lambda_j)  L(s)
###                 |  |
###                j = 1
###
###                          ___________
###                                    _
### satisfy Lambda(s) = omega Lambda(1-s), where N is a positive integer, |omega|=1,
### Each of the Gamma factors can be a Gamma_R or Gamma_C.

### Specify the conductor. Other possible keywords: N, level."""


#omega, and Gamma_R and Gamma_C factors:"""

        thefile += "\n\n"
        thefile += "conductor = " + str(self.level) + "\n\n"

        thefile += "### Specify the sign of the functional equation.\n"
        thefile += "### Complex numbers should be specified as:\n"
        thefile += "### omega = (Re(omega),Im(omega)). Other possible keyword: sign\n\n"
        if self.selfdual:
            thefile += "omega = " + str(self.sign) + "\n\n"
        else:
            thefile += "omega = " + parse_complex_number(self.sign) + "\n\n"


        thefile += "### Gamma_{R or C}_list lists the associated lambda_j's. Lines with empty lists can be omitted.\n\n"
        thefile += "Gamma_R_list = " +  str(self.mu_fe) + "\n"
        thefile += "Gamma_C_list = " +  str(self.nu_fe) + "\n\n"

        thefile += """\
##########################################################################################################
### Specify, as lists, the poles and residues of L(s) in Re(s)>1/2 (i.e. assumes that there are no
### poles on s=1/2). Also assumes that the poles are simple. Lines with empty lists can be omitted."""
        thefile += "\n\n"
        if hasattr(self, 'poles_L'):
            thefile += "pole_list = " +  str(self.poles_L) + "\n"
        else:
            thefile += "pole_list = []\n"

        if hasattr(self, 'residues_L'):
            thefile += "residue_list = " +  str(self.residues_L) + "\n\n"
        else:
            thefile += "residue_list = []\n\n"

        thefile += """\
##########################################################################################################
### Optional:"""

        thefile += "\n\n"

        thefile += "name = \"" + url.partition('/L/')[2].partition('?download')[0].strip('/') + "\"\n"
        kind = url.partition('/L/')[2].partition('?download')[0].partition('/')[0]
        kind_of_L = url.partition('/L/')[2].partition('?download')[0].split('/')
        #thefile += str(kind_of_L) + "\n\n\n\n"
        if len(kind_of_L)>2:
            thefile += "kind = \"" + kind_of_L[0] + "/" + kind_of_L[1] + "\"\n\n"
        elif len(kind_of_L)==2:
            thefile += "kind = \"" + kind_of_L[0] + "\"\n\n"

        thefile += """\
##########################################################################################################
### Specify the Dirichlet coefficients, whether they are periodic
### (relevant for Dirichlet L-functions), and whether to normalize them
### if needed to get a functional equation s <--> 1-s
###
### periodic should be set to either True (in the case of Dirichlet L-functions,
### for instance), or False (the default). If True, then lcalc assumes that the coefficients
### given, a[0]...a[N], specify all a[n] with a[n]=a[m] if n=m mod (N+1).
### For example, for the real character mod 4, one should,
### have periodic = True and at the bottom of this file, then specify:
### dirichlet_coefficient =[
### 0,
### 1,
### 0,
### -1
### ]
###
### Specify whether Dirichlet coefficients are periodic:"""
        thefile += "\n\n"
        if(self.coefficient_period!=0 or hasattr(self, 'is_zeta')):
            thefile += "periodic = True\n\n"
        else:
            thefile += "periodic = False\n\n"


        thefile += """\
##########################################################################################################
### The default is to assume that the Dirichlet coefficients are provided
### normalized so that the functional equation is s <--> 1-s, i.e. `normalize_by'
### is set to 0 by default.
###
### Sometimes, such as for an elliptic curve L-function, it is more convenient to
### record the Dirichlet coefficients normalized differently, for example, as
### integers rather than as floating point approximations.
###
### For example, an elliptic curve L-function is assumed by lcalc to be of the
### form:
###
###     L(s) = sum (a(n)/n^(1/2)) n^(-s),
###
### i.e. to have Dirichlet coefficients a(n)/n^(1/2) rather than a(n),
### where a(p) = p+1-#E(F_p), and functional equation of the form
###
###     Lambda(s):=(sqrt(N)/(2 pi))^s Gamma(s+1/2) L(s) = omega Lambda(1-s),
###
### where omega = \pm 1.
###
### So, the normalize_by variable is meant to allow the convenience, for example,
### of listing the a(n)'s rather than the a(n)/sqrt(n)'s."""
        thefile += "\n\n"

        if hasattr(self, 'normalize_by'):
            thefile += "normalize_by = " + str(self.normalize_by) +  "    ### floating point is also okay.\n"
            thefile += "### Normalize, below, the n-th Dirichlet coefficient by n^(" +str(self.normalize_by) + ")\n\n"
        else:
            thefile += "normalize_by = 0    # the default, i.e. no normalizing\n\n"

        thefile += """\
##########################################################################################################
### The last entry must be the dirichlet_coefficient list, one coefficient per
### line, separated # by commas. The 0-th entry is ignored unless the Dirichlet
### coefficients are periodic. One should always include it, however, because, in
### computer languages such as python, the 0-th entry is the `first' entry of an
### array. Since this file is meant to be compatible also with python, we assume
### that the 0-th entry is also listed.
###
### Complex numbers should be entered, as usual as a pair of numbers, separated
### by a comma. If no complex numbers appear amongst the Dirichlet coefficients,
### lcalc will assume the L-function is self-dual."""
        thefile += "\n\n"


        thefile += "Dirichlet_coefficient = [\n"

        if hasattr(self, 'is_zeta'):
            thefile += "1    ### the Dirichlet coefficients of zeta are all 1\n]\n"

        else:
            thefile += "0,\t\t\t### set Dirichlet_coefficient[0]\n"
            if hasattr(self, 'dirichlet_coefficients_unnormalized'):
                for n in range(0,len(self.dirichlet_coefficients_unnormalized)):
                    if self.selfdual:
                        thefile += str(self.dirichlet_coefficients_unnormalized[n])
                    else:
                        thefile += parse_complex_number(self.dirichlet_coefficients_unnormalized[n])
                    if n<2:
                        thefile += ",\t\t\t### set Dirichlet_coefficient[" + str(n+1) +"] \n"
                    else:
                        thefile += ",\n"
            else:
                for n in range(0,len(self.dirichlet_coefficients)):
                    if self.selfdual:
                        thefile += str(self.dirichlet_coefficients[n])
                    else:
                        thefile += parse_complex_number(self.dirichlet_coefficients[n])
                    if n<2:
                        thefile += ",\t\t\t### set Dirichlet_coefficient[" + str(n+1) +"] \n"
                    else:
                        thefile += ",\n"
            thefile = thefile[:-2]
            thefile += "]\n"

        return(thefile)


    ############################################################################
    ### other useful methods
    ############################################################################

    def original_mathematical_object(self):
        raise Error("not all L-function have a mathematical object tag defined atm")

    def initial_zeroes(self, numzeroes=0):
        pass

    def critical_value(self):
        pass

    def value_at_1(self):
        pass

    def conductor(self, advocate):
        # Advocate could be IK, CFKRS or B
        pass

    ############################################################################
    ### Injects into the database of all the L-functions
    ############################################################################

    def inject_database(self, relevant_info, time_limit = None):
        #   relevant_methods are text strings 
        #    desired_database_fields = [Lfunction.original_mathematical_object, Lfunction.level]
        #    also zeroes, degree, conductor, type, real_coeff, rational_coeff, algebraic_coeff, critical_value, value_at_1, sign
        #    ok_methods = [Lfunction.math_id, Lfunction.level]
        #
        # Is used to inject the data in relevant_fields

        logger.info("Trying to inject")
        import base
        db = base.getDBConnection().Lfunctions
        Lfunctions = db.full_collection
        update_dict = dict([(method_name,get_attr_or_method(self,method_name)) for method_name in relevant_info])

        logger.info("injecting " + str(update_dict))
        search_dict = {"original_mathematical_object()": get_attr_or_method(self, "original_mathematical_object()")}

        my_find_update(Lfunctions, search_dict, update_dict)


#############################################################################

class Lfunction_EC(Lfunction):
    """Class representing an elliptic curve L-function
    It can be called with a dictionary of these forms:

    dict = { 'label': ... }  label is the Cremona label of the elliptic curve
    dict = { 'label': ... , 'numcoeff': ...  }  numcoeff is the number of
           coefficients to use when computing
    """

    def __init__(self, **args):
        #Check for compulsory arguments
        if not 'label' in args.keys():
            raise Exception("You have to supply a label for an elliptic curve L-function")

        # Initialize default values
        self.numcoeff = 500 # set default to 500 coefficients

        # Put the arguments into the object dictionary
        self.__dict__.update(args)
        self.numcoeff = int(self.numcoeff)


        # Create the elliptic curve
        self.E = EllipticCurve(str(self.label))

        # Extract the L-function information from the elliptic curve
        self.quasidegree = 1
        self.level = self.E.conductor()
        self.Q_fe = float(sqrt(self.level)/(2*math.pi))
        self.sign = self.E.lseries().dokchitser().eps
        self.kappa_fe = [1]
        self.lambda_fe = [0.5]
        self.mu_fe = []
        self.nu_fe = [Rational('1/2')]
        self.langlands = True
        self.degree = 2

        self.dirichlet_coefficients = self.E.anlist(self.numcoeff)[1:]  #remove a0
        self.dirichlet_coefficients_unnormalized = self.dirichlet_coefficients[:]
        self.normalize_by = Rational('1/2')

        # Renormalize the coefficients
        for n in range(0,len(self.dirichlet_coefficients)-1):
           an = self.dirichlet_coefficients[n]
           self.dirichlet_coefficients[n]=float(an)/float(sqrt(n+1))

        self.poles = []
        self.residues = []
        self.coefficient_period = 0
        self.selfdual = True
        self.primitive = True
        self.coefficient_type = 2
        self.texname = "L(s,E)"
        self.texnamecompleteds = "\\Lambda(s,E)"
        self.texnamecompleted1ms = "\\Lambda(1-s,E)"
        self.title = "L-function $L(s,E)$ for the Elliptic Curve over Q with label "+ self.E.label()

        self.properties = [('Degree ','%s' % self.degree)]
        self.properties.append(('Level', '%s' % self.level))
        self.credit = 'Sage'
        self.citation = ''
        
        self.sageLfunction = lc.Lfunction_from_elliptic_curve(self.E, self.numcoeff)

        logger.info("I am now proud to have ", str(self.__dict__))
        constructor_logger(self,args)

    def Ltype(self):
        return "ellipticcurve"
        
    def ground_field(self):
        return "Q"
        # At the moment
    
    def original_mathematical_object(self):
        return [self.Ltype(), self.ground_field(), self.label]
        
            
#############################################################################

class Lfunction_EMF(Lfunction):
    """Class representing an elliptic modular form L-function

    Compulsory parameters: weight
                           level

    Possible parameters: character
                         label
                         number
    
    """
    
    def __init__(self, **args):

        #Check for compulsory arguments
        if not ('weight' in args.keys() and 'level' in args.keys()):
            raise KeyError, "You have to supply weight and level for an elliptic modular form L-function"
        logger.debug(str(args))
        # Initialize default values
        if not args['character']:
            args['character'] = 0  # Trivial character is default
        if not args['label']:
            args['label']='a'      # No label, is OK If space is one-dimensional
        if not args['number']:
            args['number'] = 0     # Default choice of embedding of the coefficients

        # Put the arguments into the object dictionary
        self.__dict__.update(args)
        logger.debug(str(self.character)+str(self.label)+str(self.number))
        self.weight = int(self.weight)
        self.level = int(self.level)
        self.character = int(self.character)
        self.number = int(self.number)

        # Create the modular form
        self.MF = WebNewForm(self.weight, self.level, self.character, self.label)
        logger.debug(str(self.MF))
        # Extract the L-function information from the elliptic modular form
        self.automorphyexp = float(self.weight-1)/float(2)
        self.Q_fe = float(sqrt(self.level)/(2*math.pi))

        if self.level == 1:  # For level 1, the sign is always plus
            self.sign = 1
        else:  # for level not 1, calculate sign from Fricke involution and weight
            self.sign = self.MF.atkin_lehner_eigenvalues()[self.level] * (-1)**(float(self.weight/2))

        self.kappa_fe = [1]
        self.lambda_fe = [self.automorphyexp]
        self.mu_fe = []
        self.nu_fe = [self.automorphyexp]
        self.selfdual = True
        self.langlands = True
        self.primitive = True
        self.degree = 2
        self.poles = []
        self.residues = []
        self.numcoeff = int(math.ceil(self.weight * sqrt(self.level))) #just testing  NB: Need to learn how to use more coefficients
        self.dirichlet_coefficients = []

        # Appending list of Dirichlet coefficients
        GaloisDegree = self.MF.degree()  #number of forms in the Galois orbit
        if GaloisDegree == 1:
           self.dirichlet_coefficients = self.MF.q_expansion_embeddings(
               self.numcoeff+1)[1:self.numcoeff+1] #when coeffs are rational, q_expansion_embedding()
                                                   #is the list of Fourier coefficients
        else:
           for n in range(1,self.numcoeff+1):
              self.dirichlet_coefficients.append(self.MF.q_expansion_embeddings(self.numcoeff+1)[n][self.number])
        for n in range(1,len(self.dirichlet_coefficients)+1):
            an = self.dirichlet_coefficients[n-1]
            self.dirichlet_coefficients[n-1]=float(an)/float(n**self.automorphyexp)
#FIX: These coefficients are wrong; too large and a1 is not 1

        self.coefficient_period = 0
        self.coefficient_type = 2
        self.quasidegree = 1

        self.checkselfdual()

        self.texname = "L(s,f)"
        self.texnamecompleteds = "\\Lambda(s,f)"
        if self.selfdual:
            self.texnamecompleted1ms = "\\Lambda(1-s,f)"
        else:
            self.texnamecompleted1ms = "\\Lambda(1-s,\\overline{f})"
        self.title = "$L(s,f)$, "+ "where $f$ is a holomorphic cusp form with weight "+str(self.weight)+", level "+str(self.level)+", and character "+str(self.character)

        self.citation = ''
        self.credit = ''

        self.generateSageLfunction()
        constructor_logger(self,args)


    def Ltype(self):
        return "ellipticmodularform"


#############################################################################

class RiemannZeta(Lfunction):
    """Class representing the Riemann zeta fucntion

    Possible parameters: numcoeff  (the number of coefficients when computing)

    """
 
    def __init__(self, **args):
        constructor_logger(self,args)

        # Initialize default values
        self.numcoeff = 30 # set default to 30 coefficients

        # Put the arguments into the object dictionary
        self.__dict__.update(args)
        self.numcoeff = int(self.numcoeff)

        self.coefficient_type = 1
        self.quasidegree = 1
        self.Q_fe = float(1/sqrt(math.pi))
        self.sign = 1
        self.kappa_fe = [0.5]
        self.lambda_fe = [0]
        self.mu_fe = [0]
        self.nu_fe = []
        self.langlands = True
        self.degree = 1
        self.level = 1
        self.dirichlet_coefficients = []
        for n in range(self.numcoeff):
            self.dirichlet_coefficients.append(1)
        self.poles = [0,1]
        self.residues = [-1,1]
        self.poles_L = [1] # poles of L(s), used by createLcalcfile_ver2
        self.residues_L = [1] # residues of L(s) createLcalcfile_ver2
        self.coefficient_period = 0
        self.selfdual = True
        self.texname = "\\zeta(s)"
        self.texnamecompleteds = "\\xi(s)"
        self.texnamecompleted1ms = "\\xi(1-s)"
        self.credit = 'Sage'
        self.primitive = True
        self.citation = ''
        self.title = "Riemann Zeta-function: $\\zeta(s)$"
        self.is_zeta = True

        self.sageLfunction = lc.Lfunction_Zeta()

    def Ltype(self):
        return "riemann"

    def original_mathematical_object(self):
        return ["riemann"]

#############################################################################

class Lfunction_Dirichlet(Lfunction):
    """Class representing the L-function of a Dirichlet character

    Compulsory parameters: charactermodulus
                           characternumber

    Possible parameters: numcoeff  (the number of coefficients when computing)
    
    """
    
    def __init__(self, **args):

        #Check for compulsory arguments
        if not ('charactermodulus' in args.keys() and 'characternumber' in args.keys()):
            raise KeyError, "You have to supply charactermodulus and characternumber for the L-function of a Dirichlet character"
        
        # Initialize default values
        self.numcoeff = 30    # set default to 30 coefficients

        # Put the arguments into the object dictionary
        self.__dict__.update(args)
        self.charactermodulus = int(self.charactermodulus)
        self.characternumber = int(self.characternumber)
        self.numcoeff = int(self.numcoeff)

        # Create the Dirichlet character
        chi = DirichletGroup(self.charactermodulus)[self.characternumber]

        if chi.is_primitive():

            # Extract the L-function information from the Dirichlet character
            # Warning: will give nonsense if character is not primitive
            aa = int((1-chi(-1))/2)   # usually denoted \frak a
            self.quasidegree = 1
            self.Q_fe = float(sqrt(self.charactermodulus)/sqrt(math.pi))
            self.sign = 1/(I**aa * float(sqrt(self.charactermodulus))/(chi.gauss_sum_numerical()))
            self.kappa_fe = [0.5]
            self.lambda_fe = [0.5*aa]
            self.mu_fe = [aa]
            self.nu_fe = []
            self.langlands = True
            self.primitive = True
            self.degree = 1
            self.coefficient_period = self.charactermodulus
            self.level = self.charactermodulus
            self.numcoeff = self.coefficient_period

            self.dirichlet_coefficients = []
            for n in range(1,self.numcoeff):
                self.dirichlet_coefficients.append(chi(n).n())

            self.poles = []
            self.residues = []

            # Determine if the character is real (i.e., if the L-function is selfdual)
            chivals=chi.values_on_gens()
            self.selfdual = True
            for v in chivals:
                if abs(imag_part(v)) > 0.0001:
                    self.selfdual = False

            if self.selfdual:
                self.coefficient_type = 1
                for n in range(0,self.numcoeff-1):
                    self.dirichlet_coefficients[n]= int(round(self.dirichlet_coefficients[n]))
            else:
                self.coefficient_type = 2

            self.texname = "L(s,\\chi)"
            self.texnamecompleteds = "\\Lambda(s,\\chi)"

            if self.selfdual:
                self.texnamecompleted1ms = "\\Lambda(1-s,\\chi)"
            else:
                self.texnamecompleted1ms = "\\Lambda(1-s,\\overline{\\chi})"

            self.credit = 'Sage'
            self.citation = ''
            self.title = "Dirichlet L-function: $L(s,\\chi)$"
            self.title = (self.title+", where $\\chi$ is the character modulo "+
                              str(self.charactermodulus) + ", number " +
                              str(self.characternumber))

            self.sageLfunction = lc.Lfunction_from_character(chi)

        else:  #Character not primitive
            raise Exception("The dirichlet character you choose is " +
                            "not primitive so it's Dirichlet series " +
                            "is not an L-function." ,"UserError")

        constructor_logger(self,args)

    def Ltype(self):
        return "dirichlet"

    def original_mathematical_object(self):
        return [self.Ltype(), self.charactermodulus, self.characternumber]


#############################################################################

class Lfunction_Maass(Lfunction):
    """Class representing the L-function of a Maass form 

    Compulsory parameters: dbid

    Possible parameters: dbName  (the name of the database for the Maass form)
                         dbColl  (the name of the collection for the Maass form)
    
    """
    
    def __init__(self, **args):
        constructor_logger(self,args)

        #Check for compulsory arguments
        if not 'dbid' in args.keys():
            raise KeyError, "You have to supply dbid for the L-function of a Maass form"
        
        # Initialize default values
        self.dbName = 'MaassWaveForm'    # Set default database
        self.dbColl = 'HT'               # Set default collection    

        # Put the arguments into the object dictionary
        self.__dict__.update(args)

        # Fetch the information from the database
        import base
        connection = base.getDBConnection()
        db = pymongo.database.Database(connection, self.dbName)
        collection = pymongo.collection.Collection(db, self.dbColl)
        dbEntry = collection.find_one({'_id':self.dbid})

        if self.dbName == 'Lfunction':  # Data from Lemurell

            # Extract the L-function information from the database entry
            self.__dict__.update(dbEntry)

            self.coefficient_period = 0
            self.poles = []
            self.residues = []

            # Extract the L-function information from the lcalfile in the database
            self.parseLcalcfile(self.lcalcfile)

        else: # GL2 data from Then or Stromberg

            self.group = 'GL2'

            # Extract the L-function information from the database entry
            self.symmetry = dbEntry['Symmetry']
            self.eigenvalue = float(dbEntry['Eigenvalue'])
            self.norm = dbEntry['Norm']
            self.dirichlet_coefficients = dbEntry['Coefficient']

            if 'Level' in dbEntry.keys():
                self.level = int(dbEntry['Level'])
            else:
                self.level = 1
            self.charactermodulus = self.level

            if 'Weight' in dbEntry.keys():
                self.weight = int(dbEntry['Weight'])
            else:
                self.weight = 0

            if 'Character' in dbEntry.keys():
                self.characternumber = int(dbEntry['Character'])

            if self.level > 1:
                try:
                    self.fricke = dbEntry['Fricke']  #no fricke for level 1
                except:
                    logger.critical('No Fricke information for Maass form')
                    self.fricke = 1

            # Set properties of the L-function
            self.coefficient_type = 2
            self.selfdual = True
            self.primitive = True
            self.quasidegree = 2
            self.Q_fe = float(sqrt(self.level))/float(math.pi)

            if self.symmetry =="odd":
                aa=1
            else:
                aa=0

            if aa==0:
                self.sign = 1
            else:
                self.sign = -1

            if self.level > 1:
                self.sign = self.fricke * self.sign

            self.kappa_fe = [0.5,0.5]
            self.lambda_fe = [0.5*aa + self.eigenvalue*I, 0,5*aa - self.eigenvalue*I]
            self.mu_fe = [aa + 2*self.eigenvalue*I, aa -2*self.eigenvalue*I]
            self.nu_fe = []
            self.langlands = True
            self.degree = 2
            self.poles = []
            self.residues = []
            self.coefficient_period = 0

            self.checkselfdual()

            self.texname = "L(s,f)"
            self.texnamecompleteds = "\\Lambda(s,f)"

            if self.selfdual:
                self.texnamecompleted1ms = "\\Lambda(1-s,f)"
            else:
                self.texnamecompleted1ms = "\\Lambda(1-s,\\overline{f})"

            self.title = "$L(s,f)$, where $f$ is a Maass cusp form with level "+str(self.level)+", and eigenvalue "+str(self.eigenvalue)
            self.citation = ''
            self.credit = ''

        self.generateSageLfunction()

    def Ltype(self):
        return "maass"
#############################################################################

class DedekindZeta(Lfunction):   # added by DK
    """Class representing the Dedekind zeta-fucntion

    Compulsory parameters: label

    """

    def __init__(self, **args):
        constructor_logger(self,args)

        #Check for compulsory arguments
        if not 'label' in args.keys():
            raise Exception("You have to supply a label for a Dedekind zeta function")

        # Initialize default values

        # Put the arguments into the object dictionary
        self.__dict__.update(args)

        # Fetch the polynomial of the field from the database
        import base
        connection = base.getDBConnection()
        db = connection.numberfields.fields
        poly_coeffs = db.find_one({'label':self.label})['coefficients']

        # Extract the L-function information from the polynomial
        R = QQ['x']; (x,) = R._first_ngens(1)
        self.polynomial = sum([poly_coeffs[i]*x**i for i in range(len(poly_coeffs))])
        self.NF = NumberField(self.polynomial, 'a')
        self.signature = self.NF.signature()
        self.sign = 1
        self.quasidegree = sum(self.signature)
        self.level = self.NF.discriminant().abs()
        self.degreeofN = self.NF.degree()

        self.Q_fe = float(sqrt(self.level)/(2**(self.signature[1]) * (math.pi)**(float(self.degreeofN)/2.0)))

        self.kappa_fe = self.signature[0]* [0.5] + self.signature[1] * [1]
        self.lambda_fe = self.quasidegree * [0]
        self.mu_fe = self.signature[0]*[0] # not in use?
        self.nu_fe = self.signature[1]*[0] # not in use?
        self.langlands = True
        self.degree = self.signature[0] + 2 * self.signature[1] # N = r1 +2r2
        self.dirichlet_coefficients = [Integer(x) for x in self.NF.zeta_coefficients(5000)]
        self.h=self.NF.class_number()
        self.R=self.NF.regulator()
        self.w=len(self.NF.roots_of_unity())
        self.h=self.NF.class_number()
        self.res=RR(2**self.signature[0]*self.h*self.R/self.w) #r1 = self.signature[0]

        self.poles = [1,0] # poles of the Lambda(s) function
        self.residues = [self.res,-self.res] # residues of the Lambda(s) function

        self.poles_L = [1] # poles of L(s) used by createLcalcfile_ver2
        self.residues_L = [1234] # residues of L(s) used by createLcalcfile_ver2, XXXXXXXXXXXX needs to be set

        self.coefficient_period = 0
        self.selfdual = True
        self.primitive = True
        self.coefficient_type = 0
        self.texname = "\\zeta_K(s)"
        self.texnamecompleteds = "\\Lambda_K(s)"
        if self.selfdual:
            self.texnamecompleted1ms = "\\Lambda_K(1-s)"
        else:
            self.texnamecompleted1ms = "\\Lambda_K(1-s)"
        self.title = "Dedekind zeta-function: $\\zeta_K(s)$"
        self.title = self.title+", where $K$ is the "+ str(self.NF)
        self.credit = 'Sage'
        self.citation = ''
        
        self.generateSageLfunction()

    def Ltype(self):
        return "dedekindzeta"
        

class ArtinLfunction(Lfunction):
    pass

class SymmetricPowerLfunction(Lfunction):
    pass
