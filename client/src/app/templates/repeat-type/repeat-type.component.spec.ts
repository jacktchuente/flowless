import { ComponentFixture, TestBed } from '@angular/core/testing';

import { RepeatTypeComponent } from './repeat-type.component';

describe('RepeatTypeComponent', () => {
  let component: RepeatTypeComponent;
  let fixture: ComponentFixture<RepeatTypeComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [RepeatTypeComponent]
    })
    .compileComponents();

    fixture = TestBed.createComponent(RepeatTypeComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
