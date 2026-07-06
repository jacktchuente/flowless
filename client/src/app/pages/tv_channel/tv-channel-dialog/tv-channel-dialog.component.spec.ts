import {ComponentFixture, TestBed} from '@angular/core/testing';
import {MAT_DIALOG_DATA, MatDialogRef} from "@angular/material/dialog";
import {NoopAnimationsModule} from "@angular/platform-browser/animations";
import {TranslateModule} from "@ngx-translate/core";
import {Subject} from "rxjs";
import {CustomFormlyModule} from "../../../custom-formly.module";
import {NotificationService} from "@project-shared/services/notification.service";
import {TvChannelService} from "@project-services/tv-channel.service";
import {TvChannelDialogComponent} from './tv-channel-dialog.component';

describe('TvChannelDialogComponent', () => {
  let fixture: ComponentFixture<TvChannelDialogComponent>;
  let component: TvChannelDialogComponent;
  let suggestSubject: Subject<{isOk: boolean, body: unknown}>;

  beforeEach(async () => {
    suggestSubject = new Subject();
    await TestBed.configureTestingModule({
      imports: [
        TvChannelDialogComponent,
        CustomFormlyModule,
        NoopAnimationsModule,
        TranslateModule.forRoot(),
      ],
      providers: [
        {provide: TvChannelService, useValue: {suggestName: () => suggestSubject}},
        {provide: NotificationService, useValue: {notify: () => undefined}},
        {provide: MatDialogRef, useValue: {close: () => undefined}},
        {
          provide: MAT_DIALOG_DATA,
          useValue: {
            channel: {id: 1, name: 'Old name', description: '', specification: '', catalog: 3},
            catalogs: [{id: 3, name: 'Catalogue', description: ''}],
          },
        },
      ],
    }).compileComponents();

    fixture = TestBed.createComponent(TvChannelDialogComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('puts the suggested name straight into the name field', () => {
    component.suggestName();
    suggestSubject.next({isOk: true, body: {name: ' Nova Prime '}});
    fixture.detectChanges();

    expect(component.form.get('name')?.value as unknown).toBe('Nova Prime');
    expect(component.model.name).toBe('Nova Prime');
    const input: HTMLInputElement | null = fixture.nativeElement.querySelector('input');
    expect(input?.value).toBe('Nova Prime');
  });

  it('keeps the current name when the request fails', () => {
    component.suggestName();
    suggestSubject.next({isOk: false, body: null});
    fixture.detectChanges();

    expect(component.model.name).toBe('Old name');
    expect(component.isSuggestingName).toBeFalse();
  });
});
