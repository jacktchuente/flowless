import { ComponentFixture, TestBed } from '@angular/core/testing';

import { MediaSourceComponent } from './media-source.component';

describe('MediaSourceComponent', () => {
  let component: MediaSourceComponent;
  let fixture: ComponentFixture<MediaSourceComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [MediaSourceComponent]
    })
    .compileComponents();

    fixture = TestBed.createComponent(MediaSourceComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
