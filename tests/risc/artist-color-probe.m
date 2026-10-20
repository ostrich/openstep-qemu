/*
 * Native NEXTSTEP Artist color and backing-store exercise.
 * Build with the native compiler: cc -O2 artist-color-probe.m -lNeXT -o artist-color-probe
 * Run from a disposable desktop Terminal; the program changes window focus.
 */
#import <appkit/Application.h>
#import <appkit/Window.h>
#import <appkit/View.h>
#import <appkit/Menu.h>
#import <appkit/graphics.h>
#import <dpsclient/psops.h>
#include <stdio.h>

static Window *main_window, *cover_window;
static int phase;

static void tick(DPSTimedEntry entry, double now, void *data)
{
    (void)entry;
    (void)now;
    (void)data;
    phase++;
    if (phase == 5) {
        puts("COVER");
        [cover_window makeKeyAndOrderFront:nil];
    } else if (phase == 10) {
        puts("RESTORED");
        [cover_window orderOut:nil];
        [main_window makeKeyAndOrderFront:nil];
    } else if (phase == 15) {
        puts("MOVED");
        [main_window moveTo:380:300];
    } else if (phase == 22) {
        puts("DONE: inspect captured pixels; lifecycle alone is not a drawing assertion");
        fflush(stdout);
        [NXApp terminate:nil];
    }
    fflush(stdout);
}

@interface ArtistColorView : View
@end
@implementation ArtistColorView
- drawSelf:(const NXRect *)rects :(int)count
{
    int i;
    static const float colors[6][3] = {
        {1, 0, 0}, {0, 1, 0}, {0, 0, 1},
        {1, 1, 0}, {0, 1, 1}, {1, 0, 1}
    };

    (void)rects;
    (void)count;
    PSsetgray(1);
    PSrectfill(0, 0, 640, 360);
    for (i = 0; i < 6; i++) {
        PSsetrgbcolor(colors[i][0], colors[i][1], colors[i][2]);
        PSrectfill(i * 100 + 12, 240, 90, 100);
    }
    for (i = 0; i < 600; i++) {
        PSsetrgbcolor(i / 599.0, 0, 0);
        PSrectfill(i + 12, 160, 1, 60);
        PSsetrgbcolor(0, i / 599.0, 0);
        PSrectfill(i + 12, 90, 1, 60);
        PSsetrgbcolor(0, 0, i / 599.0);
        PSrectfill(i + 12, 20, 1, 60);
    }
    return self;
}
@end

int main(void)
{
    NXRect frame = {{180, 180}, {640, 360}};
    NXRect cover = {{320, 240}, {300, 220}};
    Menu *menu;

    [Application new];
    menu = [Menu newTitle:"ArtistProbe"];
    [menu addItem:"Quit" action:@selector(terminate:) keyEquivalent:'q'];
    [NXApp setMainMenu:menu];
    main_window = [[Window alloc] initContent:&frame style:NX_TITLEDSTYLE
        backing:NX_BUFFERED buttonMask:NX_CLOSEBUTTONMASK defer:NO];
    [main_window setTitle:"Artist Color Recovery test"];
    [main_window setContentView:[[ArtistColorView alloc] initFrame:&frame]];
    cover_window = [[Window alloc] initContent:&cover style:NX_TITLEDSTYLE
        backing:NX_BUFFERED buttonMask:0 defer:NO];
    [cover_window setTitle:"Backing store cover"];
    [main_window display];
    [main_window makeKeyAndOrderFront:nil];
    [NXApp activateSelf:YES];
    puts("READY");
    fflush(stdout);
    DPSAddTimedEntry(1.0, tick, NULL, NX_MODALRESPTHRESHOLD);
    [NXApp run];
    return 0;
}
