import { ComponentFixture, TestBed } from '@angular/core/testing';

import { BoxContainer3Component } from './box-container3.component';

describe('BoxContainer3Component', () => {
  let component: BoxContainer3Component;
  let fixture: ComponentFixture<BoxContainer3Component>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [BoxContainer3Component]
    })
    .compileComponents();

    fixture = TestBed.createComponent(BoxContainer3Component);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
