import { ComponentFixture, TestBed } from '@angular/core/testing';

import { MediaContainerDialogComponent } from './media-container-dialog.component';

describe('MediaContainerDialogComponent', () => {
  let component: MediaContainerDialogComponent;
  let fixture: ComponentFixture<MediaContainerDialogComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [MediaContainerDialogComponent]
    })
    .compileComponents();

    fixture = TestBed.createComponent(MediaContainerDialogComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
