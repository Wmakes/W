
#translated from: https://rosettacode.org/wiki/Mandelbrot_set#PPM_non_interactive

int 80 'iXmax'
int 80 'iYmax'

int 0.0 'Cx'
int 0.0 'Cy'

int -2.5 'CxMin'
int  1.5 'CxMax'
int -2.0 'CyMin'
int  2.0 'CyMax'

int 0.0 'PixelWidth'
int 0.0 'PixelHeight'

'CxMax' - 'CxMin' = 'PixelWidth'
'CyMax' - 'CyMin' = 'PixelHeight'
'PixelWidth'  / 'iXmax' = 'PixelWidth'
'PixelHeight' / 'iYmax' = 'PixelHeight'

int 0.0 'Zx'
int 0.0 'Zy'
int 0.0 'Zx2'
int 0.0 'Zy2'

int 0 'Iteration'
int 200 'IterationMax'
int 4 'ER2'

int 0 'iY'
int 0 'iX'

int 0.0 'Sum'
bool true 'Final'

while 'iY' < 'iYmax'
    'CyMin' + 'iY' * 'PixelHeight' = 'Cy'
    'iY' + 1 = 'iY'

    0 = 'iX'
    while 'iX' < 'iXmax'
        'CxMin' + 'iX' * 'PixelHeight' = 'Cx'
        'iX' + 1 = 'iX'

        0.0 = 'Zx'
        0.0 = 'Zy'
        0.0 = 'Zx2'
        0.0 = 'Zy2'

        0 = 'Iteration'

        bool true 'IterGood'
        bool true 'RadiusGood'
        while 'IterGood' && 'RadiusGood'
            'Iteration' + 1 = 'Iteration'

            2 * 'Zx' * 'Zy' + 'Cy' = 'Zy'
            'Zx2' - 'Zy2'   + 'Cx' = 'Zx'
            'Zx' * 'Zx' = 'Zx2'
            'Zy' * 'Zy' = 'Zy2'

            'Zx2' + 'Zy2' = 'Sum'
            'Sum' < 'ER2' = 'RadiusGood'
            'Iteration' < 'IterationMax' = 'IterGood'

        done

        'Iteration' == 'IterationMax' = 'Final'
        if     'Final' show "#"
        if not 'Final' show " "


    done
    show "\n"
done

