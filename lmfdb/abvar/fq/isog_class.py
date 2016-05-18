# -*- coding: utf-8 -*-


from lmfdb.utils import comma, make_logger

from lmfdb.base import getDBConnection

from sage.misc.cachefunc import cached_function
from sage.rings.all import Integer
from sage.all import PolynomialRing, QQ

from lmfdb.genus2_curves.isog_class import list_to_factored_poly_otherorder
from lmfdb.transitive_group import group_display_knowl

logger = make_logger("abvarfq")

#########################
#   Database connection
#########################

@cached_function
def db():
    return getDBConnection().abvar.fq_isog

#########################
#   Label manipulation
#########################

def validate_label(label):
    parts = label.split('.')
    if len(parts) != 3:
        raise ValueError("it must be of the form g.q.iso, with g a dimension and q a prime power")
    g, q, iso = parts
    try:
        g = int(g)
    except ValueError:
        raise ValueError("it must be of the form g.q.iso, where g is an integer")
    try:
        q = Integer(q)
        if not q.is_prime_power(): raise ValueError
    except ValueError:
        raise ValueError("it must be of the form g.q.iso, where g is a prime power")
    coeffs = iso.split("_")
    if len(coeffs) != g:
        raise ValueError("the final part must be of the form c1_c2_..._cg, with g=%s components"%(g))
    if not all(c.isalpha() and c==c.lower() for c in coeffs):
        raise ValueError("the final part must be of the form c1_c2_..._cg, with each ci consisting of lower case letters")

class AbvarFq_isoclass(object):
    """
    Class for an isogeny class of abelian varieties over a finite field
    """
    def __init__(self,dbdata):
        self.__dict__.update(dbdata)
        self.make_class()

    @classmethod
    def by_label(cls,label):
        """
        Searches for a specific isogeny class in the database by label.
        """
        try:
            data = db().find_one({"label": label})
            return cls(data)
        except AttributeError:
            raise ValueError("Label not found in database")

    def make_class(self):
        from main import decomposition_display
        self.decompositioninfo = decomposition_display(self,self.decomposition)
        self.formatted_polynomial, galois_gp = list_to_factored_poly_otherorder(self.polynomial,galois=True,vari = 'x')
        if self.is_simple():
            C = getDBConnection()
            galois_gp = galois_gp[0]
            self.galois = group_display_knowl(galois_gp[0],galois_gp[1],C)            
        
    def p(self):
        q = Integer(self.q)
        p, _ = q.is_prime_power(get_data=True)
        return p
    
    def r(self):
        q = Integer(self.q)
        _, r = q.is_prime_power(get_data=True)
        return r
        
    def field(self):
        p = self.p()
        r = self.r()
        if r == 1:
            return '\F_{' + '{0}'.format(p) + '}'
        else:
            return '\F_{' + '{0}^{1}'.format(p,r) + '}'
        
    def weil_numbers(self):
        q = self.q
        ans = ""
        for angle in self.angle_numbers:
            if ans != "":
                ans += ", "
            ans += '\sqrt{' +str(q) + '}' + '\exp(\pm i \pi {0}\ldots)'.format(angle)
            #ans += "\sqrt{" +str(q) + "}" + "\exp(-i \pi {0}\ldots)".format(angle)
        return ans
        
    def frob_angles(self):
        ans = ''
        for angle in self.angle_numbers:
            if ans != '':
                ans += ', '
            ans += '\pm' + str(angle) 
        return ans
    
    def is_simple(self):
        if len(self.decomposition) == 1:
            if self.decomposition[0][1] == 1:
                return True
        else:
            return False
            
    def is_primitive(self): #we don't know this
        if self.primitive_models == '':
            return True
        else:
            return False
            
    def is_ordinary(self):
        if self.__dict__['p_rank'] == self.__dict__['g']:
            return True
        else:
            return False
        
    def is_supersingular(self):
        for slope in self.__dict__['slopes']:
            if slope != '1/2':
                return False
        return True
        
    def display_slopes(self):
        ans = '['
        for slope in self.slopes:
            if ans != '[':
                ans += ', '
            ans += slope
        ans += ']'
        return ans
        
    def length_A_counts(self):
        return len(self.A_counts)
        
    def length_C_counts(self):
        return len(self.C_counts)
            
        

    
