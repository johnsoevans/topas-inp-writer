# Equation Operators and Functions


| Table 3-1. Operators and functions supported in equations (case sensitive). In addition, equations can be a function of User defined parameter names. | Table 3-1. Operators and functions supported in equations (case sensitive). In addition, equations can be a function of User defined parameter names. | Table 3-1. Operators and functions supported in equations (case sensitive). In addition, equations can be a function of User defined parameter names. |
| --- | --- | --- |
| Arithmetic | Arithmetic | Arithmetic |
| +, -, *, / | Plus, Minus, Multiply, Divide. Multiply is optional, x*y = x y | Plus, Minus, Multiply, Divide. Multiply is optional, x*y = x y |
| ^ | x^y, Calculates x to the power of y. Precedence:    x^y^z = (x^y)^z,     x^y*z = (x^y)*z,     x^y/z = (x^y)/z | x^y, Calculates x to the power of y. Precedence:    x^y^z = (x^y)^z,     x^y*z = (x^y)*z,     x^y/z = (x^y)/z |
| Conditional | Conditional | Conditional |
| a == b | Returns 1 if a = b | Returns 1 if a = b |
| a < b | Returns 1 if a < b | Returns 1 if a < b |
| a <= b | Returns 1 if a ≤ b | Returns 1 if a ≤ b |
| a > b | Returns 1 if a > b | Returns 1 if a > b |
| a >= b | Returns 1 if a ≥ b | Returns 1 if a ≥ b |
| And(a, b, …) | Returns 1 if all arguments are non-zero | Returns 1 if all arguments are non-zero |
| Or(a, b, …) | Returns 1 if one or more argument is non-zero | Returns 1 if one or more argument is non-zero |
| Mathematical | Mathematical | Mathematical |
| ArcCos(x) | Returns the arc cos of x (-1 <= x <= 1) | Returns the arc cos of x (-1 <= x <= 1) |
| ArcSin(x) | Returns the arc sine of x (-1 <= x <= 1) | Returns the arc sine of x (-1 <= x <= 1) |
| ArcTan(x) | Returns the arc tangent of x | Returns the arc tangent of x |
| ArcTan2(y,x) | Returns arc tangent of y/x | Returns arc tangent of y/x |
| Cos(x) | Returns the cosine of x | Returns the cosine of x |
| Cosh(x) | Hyperbolic cosine | Hyperbolic cosine |
| Erf_Approx(x) | Error function | Error function |
| Erfc_Approx | Complementary error function | Complementary error function |
| Exp(x) | Returns the exponential e to the x | Returns the exponential e to the x |
| Gamma_Approx(x) | Return the Gamma of x | Return the Gamma of x |
| Gamma_Ln_Approx(x) | Returns the natural logarithm of the gamma function | Returns the natural logarithm of the gamma function |
| Gamma_P(a, x) | Returns the incomplete Gamma function P(a, x) | Returns the incomplete Gamma function P(a, x) |
| Gamma_Q(a, x) | Returns the incomplete Gamma function Q(a, x) = 1-P(a,x) | Returns the incomplete Gamma function Q(a, x) = 1-P(a,x) |
| Ln(x) | Returns the natural logarithm of x | Returns the natural logarithm of x |
| Sin(x) | Returns the sine of x | Returns the sine of x |
| Sinh(x) | Hyperbolic sine | Hyperbolic sine |
| Sqrt(x) | Returns the positive square root | Returns the positive square root |
| Tan(x) | Returns the tangent of x | Returns the tangent of x |
| Tanh(x) | Hyperbolic tangent | Hyperbolic tangent |
| Special | Special | Special |
| For(Mi = 0, Mi < M, Mi = Mi+1 , …) | For(Mi = 0, Mi < M, Mi = Mi+1 , …) | For(Mi = 0, Mi < M, Mi = Mi+1 , …) |
| Get($keyword) | Gets the parameter associated with $keyword | Gets the parameter associated with $keyword |
| If(conditional_test, return true_eqn, return false_eqn) | If(conditional_test, return true_eqn, return false_eqn) | If(conditional_test, return true_eqn, return false_eqn) |
| Sum(returns summation_eqn, initializer, conditional_test, increment_eqn) | Sum(returns summation_eqn, initializer, conditional_test, increment_eqn) | Sum(returns summation_eqn, initializer, conditional_test, increment_eqn) |
| Miscellaneous | Miscellaneous | Miscellaneous |
| Abs(x) | Returns the absolute value of x | Returns the absolute value of x |
| Break | Can be used to terminate loops implied by the equations atomic_interaction, box_interaction and grs_interaction. | Can be used to terminate loops implied by the equations atomic_interaction, box_interaction and grs_interaction. |
| Break_Cycle | Can be used to terminate a refinement cycle. For example, a refinement cycle can be terminated depending on the value of a penalty as follows: | Can be used to terminate a refinement cycle. For example, a refinement cycle can be terminated depending on the value of a penalty as follows: |
| Break_Cycle | atomic_interaction ai = (R - 1.3)^2;  penalty = If(ai > 5, Break_Cycle, 0); | atomic_interaction ai = (R - 1.3)^2;  penalty = If(ai > 5, Break_Cycle, 0); |
| Concat(a, b, c, …) | Concatenates strings; the arguments can be parameters or strings. If an argument, then the value of the parameter is converted to a string. | Concatenates strings; the arguments can be parameters or strings. If an argument, then the value of the parameter is converted to a string. |
| Error(p) | Returns associated error of parameter p. | Returns associated error of parameter p. |
| a = Load_Eval(b) | Evaluates b on loading and places the result in a. | Evaluates b on loading and places the result in a. |
| Max(a,b,c …) | Returns the max of all arguments. | Returns the max of all arguments. |
| Min(a,b,c …) | Returns the min of all arguments. | Returns the min of all arguments. |
| Mod(x, y) | Returns the modulus of x/y. Mod(x, 0) returns 0. | Returns the modulus of x/y. Mod(x, 0) returns 0. |
| Obj_There(a) | Returns 1 if object ‘a’ exists within the current scope. | Returns 1 if object ‘a’ exists within the current scope. |
| Prm_There(a) | Returns 1 if prm/local ‘a’ exists. | Returns 1 if prm/local ‘a’ exists. |
| Rand(a, b) | Returns a uniform deviate random number between a & b. | Returns a uniform deviate random number between a & b. |
| Rand_Normal(mean,std) | Returns a random number with a normal distribution with a mean of ‘mean’ and standard deviation of ‘std’. | Returns a random number with a normal distribution with a mean of ‘mean’ and standard deviation of ‘std’. |
| Round(x) | Examples: | prm = Round(.1);   :  0.00000 prm = Round(.5);   :  0.00000 prm = Round(1.6);  :  2.00000 prm = Round(-.1);  :  0.00000 prm = Round(-.5);  :  0.00000 prm = Round(-1.6); : -2.00000 |
| To_Prm(a, b, c, …) | Concatenates the arguments to form a parameter name and returns the corresponding parameter. If an argument is a parameter name, then the value of the parameter is converted to a string. | Concatenates the arguments to form a parameter name and returns the corresponding parameter. If an argument is a parameter name, then the value of the parameter is converted to a string. |
| To_String(a) | Evaluates the parameter ‘a’ and converts the result to a string. | Evaluates the parameter ‘a’ and converts the result to a string. |
| Sign(x) | Returns the sign of x, or zero if x = 0 | Returns the sign of x, or zero if x = 0 |

In addition, the following functions are implemented:

AB_Cyl_Corr(R), AL_Cyl_Corr(R)

Returns AB and AL for cylindrical sample intensity correction (Sabine et al., 1998). These functions are used in the macros Cylindrical_I_Correction and Cylindrical_2Th_Correction. Example cylcorr.inp demonstrates usage. For a more accurate alternative to the Sabine corrections see the capillary_diameter_mm convolution.

Bkg_at(x)

Returns the value of the Chebyshev polynomial, defined by bkg, at the value x.

Constant(expression)

Evaluates ‘expression’ once and then replaces ‘Constant(expression)’ with the corresponding numeric value. Very useful when the expected change in a parameter insignificantly affects the value of a dependent equation, see for example the TOF_Exponential macro.

Ln_Normal_x_at_CD(u, s, v, toll)

Returns x value of a Ln normal distribution such that x is at the Cumulative Distribution value of ‘cd’ where u and s are the mean and standard deviation of the variable’s natural logarithm. x is calculated with a tolerance in 'cd' of 'toll'; see test_examples\wppm\ln-normal-1.inp.

PV_Lor_from_GL(gauss_FWHM, lorentzian_FWHM)

Returns the Lorentzian contribution of a pseudo-Voigt approximation to the Voigt where gauss_FWHM and lorentzian_FWHM are the FWHMs of the Gaussian and Lorentzian convoluted to form the Voigt.

Sites_Geometry_Distance($Name)

Sites_Geometry_Angle($Name)

Sites_Geometry_Dihedral_Angle($Name)

Value_at_X(object, x) : Returns the value of object at X = x. object could be a parameter or a user_y object. For example, to ensure background is close to the high angle end of a pattern during PDF-generation, the following could be implemented:


| user_y u capillary.xy fit_obj = (p0 + p1 X) u; bkg @ 0 0 0  penalty = 1000 (Bkg_at(X2) + (p0 + p1 X2) Value_at_X(u, X2) - Yobs_at(X2))^2; |
| --- |

Voigt_Integral_Breadth_GL(gauss_FWHM, lorentzian_FWHM)

Returns the integral breadth resulting from the convolution of a Gaussian with a Lorentzian with FWHMs of gauss_FWHM and Lorentzian_FWHM respectively.

Voigt_FWHM_GL(gauss_FWHM, lorentzian_FWHM)

Returns the Voigt FWHM resulting from the convolution of a Gaussian with a Lorentzian with FWHMs of gauss_FWHM and Lorentzian_FWHM respectively.

Yobs_Avg(x1, x2)

Returns the average value of Yobs between x1 and x2. x1 and x2 is first set to the closest x-axis data point.

Ycalc_at(x)

Returns the value of Ycalc at x. Zero is returned if x < X1 or x > X2.

Yobs_at(#x)

Returns the Yobs value at the x-axis position #x; can be used in all sub xdd dependent equations.

Yobs_dx_at(#x):

Returns the step size of the observed data at the x-axis position #x; can be used in all sub xdd dependent equations. If the step size in the x-axis is equidistant then Yobs_dx_at is converted to a constant corresponding to the step size in the data.

Yobs_Min(x1, x2)

Returns the minimum value of Yobs between x1 and x2.


## 'If' and nested 'If' statements

'If' statements can be used in parameter equations, for example:


| prm a 0.1 prm b 0.1 lor_fwhm = If(Mod(H, 2) == 0, a Tan(Th), b Tan(Th)); |
| --- |

'If' can also be nested:


| prm cs 200 update = If(Val < 10, 10, If(Val > 10000, 10000, Val)); |
| --- |

For those who are familiar with if/else statements, the IF THEN ELSE ENDIF macros, as defined in Topas.inc, can be used:


| IF a > b THEN a ‘ return expression value ELSE b ‘ return expression value ENDIF |
| --- |

Min and Max functions can be used in equations, for example:


| prm a 0.1 prm b 0.3 th2_offset = Min(Max(a, b, -0.2), 0.2); |
| --- |


## Floating point exceptions

An exception is thrown when an invalid floating-point operation is encountered, i.e.

Divide by zero

Sqrt(x) for x < 0

Ln(x) for x ≤ 0

ArcCos(x) for x < -1 or x> 1

Exp(x) produces an overflow for x ~ 700

(-x)^y for x  > 0 and y not an integer

Tan(x) evaluates to Infinity for x = n Pi/2, Abs(n) = 1, 3, 5, …

min/max equations, Min/Max functions or ‘If’ functions can be used to avoid invalid floating-point operations. Equations can also be rearranged to the same end – for example, Exp(-1000) in place of 1/Exp(1000).
